import os
import sys
import subprocess
import json
import glob
from datetime import datetime

"""
This script is a wrapper to download Mifit data and convert the dowloaded
tracks to TCX.

It is a part of a clone of the mifit-exporter original
project, and just executes the run.sh instructions given as example in the
original project.
"""

class GoogleToken:
    """
    Call token-cli to generate a Google token which can then be exchanged for
    a MiFit token, token-cli is provided by
    https://github.com/imduffy15/token-cli
    """
    # client-id used as example by mifit-exporter project
    clientid = \
      "571394967398-j6vs98u325la013f0ho6hehosdi2h2eb.apps.googleusercontent.com"

    def __init__(self):
        pass

    def create_token(self, gclientid="", has_session=False):
        clientid = gclientid or self.clientid

        cmd1 = ["token-cli", "target", "create", "google", "-t",
               "https://accounts.google.com/.well-known/openid-configuration"]
        cmd2 = ["token-cli", "target", "set", "google"]
        cmd3 = ["token-cli", "token", "get", clientid, "--scope", "openid"]

        if not(has_session):
            subprocess.run(cmd1)
            subprocess.run(cmd2)
        code = subprocess.check_output(cmd3)
        return code.decode("utf-8").strip()


class Track:
    def __init__(self, mifit, tracksum, details=None):
        self.mifit = mifit
        self.summary = tracksum
        self.trackid = tracksum["trackid"]
        self.source = tracksum["source"]
        self.details = details
        self.updated = False

    def is_completed(self):
        if (self.summary and self.details):
            return True
        else:
            return False

    def update(self, force=False):
        if not(self.is_completed()) or force:
            self.load_details()
            self.updated = True

    def load_details(self):
        url = "https://api-mifit-de.huami.com/v1/sport/run/detail.json?"\
              "trackid=%s&source=%s" % (self.trackid, self.source)
        cmd = ["curl", "-H", "apptoken: %s" % self.mifit.apptoken, 
               "--compressed", url]
        data = subprocess.check_output(cmd)
        data = data.decode("utf-8")
        details = json.loads(data)["data"]
        self.details = details


class MifitCache:
    """
    Save/reuse the json data of activities and track details obtained from
    Mifit servers to/from files in a dedicated 'cache' directory.
    """
    def __init__(self, mifit):
        self.mifit = mifit
        self.activities = None
        self.summary = None
        self.tracks = {}
        self.json_files = []

    def load_cache(self, cache_dir=""):
        if cache_dir:
            cwd = os.getcwd()
            os.chdir(cache_dir)

        self.json_files = glob.glob("*.json")
        self.load_activities()
        for track in self.tracks.values():
            self.load_track_details(track)

        if cache_dir:
            os.chdir(cwd)

    def dump_cache(self, cache_dir="", mifit=None):
        if cache_dir:
            cwd = os.getcwd()
            os.chdir(cache_dir)

        if mifit:
            self.activities = mifit.activities
            self.tracks = mifit.tracks
        json_dump(self.activities, "activities.json")
        for track in self.tracks.values():
            self.dump_track_details(track)

        if cache_dir:
            os.chdir(cwd)

    def load_activities(self):
        if not("activities.json" in self.json_files):
            return None
        data = open("activities.json").read()
        self.activities = json.loads(data)
        self.summary = self.activities["summary"]
        self._populate_tracks()
        return self.activities

    def _populate_tracks(self):
        for tracksum in self.summary:
            track = Track(self.mifit, tracksum)
            self.tracks[track.trackid] = track

    def load_track_details(self, track):
        track_file = "track_%s.json" % (track.trackid)
        if os.path.isfile(track_file):
            data = open(track_file).read()
            track.details = json.loads(data)

    def dump_track_details(self, track):
        track_file = "track_%s.json" % (track.trackid)
        if track.details:
            json_dump(track.details, "track_%s.json" % track.trackid)


class Mifit:
    """
    Object in charge of authenticating to Mifit, acquire the activity summary,
    and for missing activities the detailed activity.
    """
    def __init__(self):
        self.apptoken = ""
        self.activities = None
        self.summary = None
        self.tracks = {}
        self.cache = MifitCache(self)

    def load_cache(self, cache_dir):
        self.cache.load_cache(cache_dir)
        self.tracks.update(self.cache.tracks)

    def dump_cache(self, cache_dir):
        self.cache.dump_cache(cache_dir, mifit=self)

    def update_tracks(self, force=False, begin=None, end=None):
        for track in self.get_tracks(begin=begin, end=end):
            track.update(force=force)

    def get_tracks(self, begin=None, end=None):
        dates = [ trackid for trackid in self.tracks.keys() ]
        dates.sort()
        first, last = 0, len(dates)
        if begin:
            ts1 = datetime.timestamp(begin)
            for i in range(0, len(dates)):
                if int(dates[i]) >= ts1:
                    first = i
                    break
        if end:
            ts2 = datetime.timestamp(end)
            for i in range(first, len(dates)):
                if int(dates[i]) < ts2:
                    last = i
                    break
        dates = dates[first:last]
        tracks = [ self.tracks[d] for d in dates ]
        return tracks

    def login(self, google_token):
        cmd = ["curl", "-H",
               "Content-Type: application/x-www-form-urlencoded; charset=UTF-8",
               "--data-binary", "app_version=4.0.7&country_code=GB&device_id=0&third_name=google&device_model=gpx-exporter&app_name=com.xiaomi.hm.health&code=%s&grant_type=request_token" % google_token, "--compressed",
                'https://account.huami.com/v2/client/login']
        data = subprocess.check_output(cmd)
        infos = json.loads(data.decode("utf-8"))
        self.apptoken = infos["token_info"]["app_token"]

    def load_activities(self):
        cmd = ["curl", "-H", "apptoken: %s" % self.apptoken,
               "--compressed",
               'https://api-mifit-de.huami.com/v1/sport/run/history.json?source=run.34.huami.com%2Crun.watch.qogir.huami.com%2Crun.28.huami.com%2Crun.watch.huami.com%2Crun.25.huami.com%2Crun.beats.huami.com%2Crun.46.huami.com%2Crun.26.huami.com%2Crun.31.huami.com%2Crun.27.huami.com%2Crun.beatsp.huami.com%2Crun.44.huami.com%2Crun.24.huami.com%2Crun.chaohu.huami.com%2Crun.43.huami.com%2Crun.wuhan.huami.com%2Crun.30.huami.com%2Crun.45.huami.com%2Crun.watch.everests.huami.com%2Crun.tempo.huami.com%2Crun.35.huami.com%2Crun.watch.everest.huami.com%2Crun.36.huami.com%2Crun.42.huami.com%2Crun.mifit.huami.com%2Crun.41.huami.com%2Crun.chongqing.huami.com%2Crun.38.huami.com%2Crun.29.huami.com%2Crun.39.huami.com%2Crun.dongtinghu.huami.com%2Crun.37.huami.com%2Crun.40.huami.com']
        data = subprocess.check_output(cmd)
        self.activities = json.loads(data.decode("utf-8"))["data"]
        self.summary = self.activities["summary"]
        self._populate_tracks()
        return self.activities

    def _populate_tracks(self):
        for tracksum in self.summary:
            if not(tracksum["trackid"] in self.tracks):
                track = Track(self, tracksum)
                self.tracks[track.trackid] = track



def json_dump(data, output_file):
    with open(output_file, "w") as outfile:
        json.dump(data, outfile)
        outfile.close()


def main():
    from mifit_converter import convert_track_from_json
    from optparse import OptionParser

    parser = OptionParser(version="%prog", usage="%prog [options]")

    parser.add_option("--cache-in", "--ci", action='store',
              help='Specify the mifit input cache directory')
    parser.add_option("--cache-out", "--co", action='store',
              help='Specify the mifit output cache directory')
    parser.add_option("-u", "--update", action='store_true',
              help='Load latest activities from mifit servers')
    parser.add_option("-s", "--has-session", action='store_true',
              help='A google token session already running')
    parser.add_option("-l", "--list", action='store_true',
              help='List the found tracks')
    parser.add_option("-f", "--force", action='store_true',
              help='Force updating even if data already in cache')
    parser.add_option("-r", "--range", action='store',
              help='Apply on the specified date range')
    parser.add_option("-x", "--tcx", action='store_true',
              help='Export tracks to TCX')
    parser.add_option("-o", "--output-tcx-dir", action='store',
              default="",
              help='Output directory for TCX tracks')

    (options, args) = parser.parse_args()

    mifit = Mifit()

    if options.range:
        # TODO
        pass

    if options.cache_in:
        mifit.load_cache(cache_dir=options.cache_in)

    if options.update:
        google = GoogleToken()
        token = google.create_token(has_session=options.has_session)
        print("Google token:\n'%s'" % token)
        mifit.login(token)
        mifit.load_activities()
        mifit.update_tracks()

    if options.cache_out:
        mifit.dump_cache(cache_dir=options.cache_out)

    if options.list:
        for i, track in enumerate(mifit.get_tracks()):
            d = datetime.fromtimestamp(int(track.trackid))
            if not(track.is_completed()):
                status = "(uncomplete)"
            elif track.updated:
                status = "(updated)"
            else:
                status = ""
            print("%03d: %s: track_%s %s" % (i+1,
                                       d.strftime("%Y-%m-%d %H:%M:%S"),
                                       track.trackid,
                                       status))

    if options.tcx:
        for track in mifit.get_tracks():
            print("Export trackid=%s to TCX" % (track.trackid))
            tcx_file = os.path.join(options.output_tcx_dir,
                                    "track_%s.tcx" % track.trackid)
            convert_track_from_json(track.summary, track.details, tcx_file)


if __name__ == "__main__":
    main()

