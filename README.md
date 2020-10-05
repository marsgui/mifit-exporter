# mifit-export

MiFit export is a clone of the mifit-exporter project available here:
https://github.com/imduffy15/mifit-exporter

The script mifit_export.py just automate the steps described in the original
project in the README and in the run.sh script, and converts the tracks
dowloaded as json data to TCX files.

## Dependencies

The script requires that token-cli has been installed.

## Usage

```
$ python3 mifit_export.py -h
Usage: mifit_export.py [options]

Options:
  --version             show program's version number and exit
  -h, --help            show this help message and exit
  --cache-in=CACHE_IN, --ci=CACHE_IN
                        Specify the mifit input cache directory
  --cache-out=CACHE_OUT, --co=CACHE_OUT
                        Specify the mifit output cache directory
  -u, --update          Load latest activities from mifit servers
  -s, --has-session     A google token session already running
  -l, --list            List the found tracks
  -f, --force           Force updating even if data already in cache
  -r RANGE, --range=RANGE
                        Apply on the specified date range
  -x, --tcx             Export tracks to TCX
  -o OUTPUT_TCX_DIR, --output-tcx-dir=OUTPUT_TCX_DIR
                        Output directory for TCX tracks
```

With the script you can:
* Authenticate to Mifit by using token-cli.
* Update the Mifit data in json format and save them in files in a cache
  directory. The data are the activities and their details.
* Convert the json data to produce the TCX files of the downloaded tracks,
  either on the cached data (offline mode) or on the fly from the grabbed data.
* List the tracks in cache and on Mifit server. 


### Uploading to Garmin Connect

```
$ pip install garmin-uploader
```

Create `~/.guploadrc` containing your Garmin Connect login details:

```
[Credentials]
username=<username>
password=<password>
```

Upload an activity as follows:

```
$ gupload -a "Evening walk" latest.tcx 
```
