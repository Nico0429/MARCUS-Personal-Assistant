import os
import urllib.request
import zipfile
from tqdm import tqdm


ASSET_URL = "https://github.com/Nico0429/MARCUS-Personal-Assistant/releases/download/v1.0/marcus_assets.zip"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ASSETS_DIR = os.path.join(BASE_DIR, "assets")
ZIP_PATH = os.path.join(BASE_DIR, "marcus_assets.zip")

class DownloadProgressBar(tqdm):
    def update_to(self, b=1, bsize=1, tsize=None):
        if tsize is not None:
            self.total = tsize
        self.update(b * bsize - self.n)

def setup_assets():
    print("[ System ] Booting Asset Manager...")
    os.makedirs(ASSETS_DIR, exist_ok=True)

    # 1. Download the ZIP file
    print(f"[ System ] Downloading core binaries and neural models...")
    try:
        with DownloadProgressBar(unit='B', unit_scale=True, miniters=1, desc="marcus_assets.zip") as t:
            urllib.request.urlretrieve(ASSET_URL, filename=ZIP_PATH, reporthook=t.update_to)
    except Exception as e:
        print(f"\n[ CRITICAL ERROR ] Failed to download assets: {e}")
        return

    # 2. Extract the ZIP directly into the assets folder
    print("\n[ System ] Extracting assets...")
    try:
        with zipfile.ZipFile(ZIP_PATH, 'r') as zip_ref:
            zip_ref.extractall(ASSETS_DIR)
        print("[ System ] Extraction complete.")
    except Exception as e:
        print(f"[ CRITICAL ERROR ] Failed to unzip files: {e}")
        return

    # 3. Clean up the ZIP file
    try:
        os.remove(ZIP_PATH)
        print("[ System ] Cleaned up temporary files.")
    except:
        pass

    print("\n[ System ] Asset Setup Successful! You can now boot main.py.")

if __name__ == "__main__":
    setup_assets()