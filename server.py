"""
FastMCP Image Downloader with proper cancellation handling
"""
from mcp.server.fastmcp import FastMCP
from mcp.types import NotificationParams, Notification, RootModel
from typing import Literal
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
import logging
from logging.handlers import RotatingFileHandler
import os
import time
import urllib.request
from datetime import datetime
import tempfile
import shutil
from typing import Dict
import traceback
from contextlib import contextmanager

# Add Cancelled Notification support
class CancelledNotificationParams(NotificationParams):
    """Parameters for Cancel notification"""
    reason: str | None = None

class CancelledNotification(Notification):
    """Notification for cancellation"""
    method: Literal["cancelled"]
    params: CancelledNotificationParams

# Configure logging
LOG_DIR = 'D:\\DJVIBE\\MCP\\mcp-image-downloader\\logs'
LOG_FILE = os.path.join(LOG_DIR, 'server.log')
os.makedirs(LOG_DIR, exist_ok=True)

# Configure rotating file handler
file_handler = RotatingFileHandler(
    LOG_FILE,
    maxBytes=5*1024*1024,  # 5MB
    backupCount=5,
    encoding='utf-8'
)
file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))

# Console output
console_handler = logging.StreamHandler()
console_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))

# Setup logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
logger.addHandler(file_handler)
logger.addHandler(console_handler)

# Create MCP server
mcp = FastMCP("Image Downloader")

@contextmanager
def safe_file_operation():
    """Context manager for safe file operations"""
    temp_dir = tempfile.mkdtemp()
    temp_file = os.path.join(temp_dir, 'temp_image.jpg')
    try:
        yield temp_file
    finally:
        try:
            shutil.rmtree(temp_dir)
        except Exception as e:
            logger.error(f"Error cleaning temp files: {e}")

@mcp.tool()
def download_images(
    query: str,
    num_images: int = 5,
    min_size: int = 180,
    image_type: str = "photo"
) -> Dict:
    """Download high-resolution images from Google Images."""
    driver = None
    downloaded_files = []
    total_attempts = 0
    
    try:
        logger.info(f"Starting download for query: {query}")
        min_size_bytes = min_size * 1024
        search_dir = os.path.join("D:\\DJVIBE\\DOCS\\ARTICLES\\images", query.replace(" ", "_"))
        os.makedirs(search_dir, exist_ok=True)

        # Setup Chrome
        options = Options()
        options.add_argument('--headless=new')
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        service = Service("D:\\DJVIBE\\TOOLS\\chromedriver-win64\\chromedriver.exe")
        driver = webdriver.Chrome(service=service, options=options)

        try:
            logger.info("Navigating to Google Images...")
            driver.get("https://www.google.com/imghp")
            search_box = driver.find_element(By.NAME, "q")
            search_box.clear()
            search_box.send_keys(query + Keys.RETURN)
            time.sleep(2)

            if image_type != "all":
                try:
                    logger.info(f"Setting image type filter...")
                    tools_button = WebDriverWait(driver, 10).until(
                        EC.element_to_be_clickable((By.XPATH, "//div[text()='Tools']"))
                    )
                    tools_button.click()
                    time.sleep(1)
                    
                    type_button = WebDriverWait(driver, 10).until(
                        EC.element_to_be_clickable((By.XPATH, "//div[text()='Type']"))
                    )
                    type_button.click()
                    time.sleep(1)
                    
                    type_option = WebDriverWait(driver, 10).until(
                        EC.element_to_be_clickable((By.XPATH, f"//div[text()='{image_type.capitalize()}']"))
                    )
                    type_option.click()
                    time.sleep(2)
                except Exception as e:
                    logger.warning(f"Could not set image type filter: {str(e)}")

            downloaded = 0
            scrolls = 0
            
            while downloaded < num_images and scrolls < 10:
                containers = driver.find_elements(By.CSS_SELECTOR, 'div[jsname="dTDiAc"]')
                logger.debug(f"Found {len(containers)} image containers")
                
                for container in containers[downloaded:]:
                    if downloaded >= num_images:
                        break

                    try:
                        total_attempts += 1
                        driver.execute_script("arguments[0].scrollIntoView(true);", container)
                        time.sleep(0.5)
                        container.click()
                        time.sleep(1)

                        high_res_img = WebDriverWait(driver, 10).until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, 'img.sFlh5c.FyHeAf.iPVvYb'))
                        )
                        
                        img_url = high_res_img.get_attribute('src')
                        if not img_url or not img_url.startswith('http'):
                            continue
                            
                        with safe_file_operation() as temp_file:
                            headers = {
                                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36'
                            }
                            
                            req = urllib.request.Request(img_url, headers=headers)
                            with urllib.request.urlopen(req, timeout=10) as response, open(temp_file, 'wb') as out_file:
                                data = response.read()
                                out_file.write(data)
                            
                            file_size = os.path.getsize(temp_file)
                            logger.debug(f"Downloaded file size: {file_size/1024:.1f}KB")
                            
                            if file_size >= min_size_bytes:
                                timestamp = datetime.now().strftime("%H%M%S")
                                filename = f"{query.replace(' ', '_')}_{timestamp}_{downloaded+1}.jpg"
                                filepath = os.path.join(search_dir, filename)
                                
                                shutil.move(temp_file, filepath)
                                downloaded += 1
                                downloaded_files.append(filepath)
                                logger.info(f"Downloaded image {downloaded}/{num_images}")

                    except Exception as e:
                        logger.error(f"Error processing image: {str(e)}")
                        continue

                if downloaded < num_images:
                    scrolls += 1
                    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                    time.sleep(1)

            logger.info(f"Download complete. Got {len(downloaded_files)}/{num_images} images")
            return {
                "status": "success",
                "downloaded": len(downloaded_files),
                "files": downloaded_files,
                "attempts": total_attempts
            }

        finally:
            if driver:
                try:
                    logger.info("Closing Chrome browser...")
                    driver.quit()
                except Exception as e:
                    logger.error(f"Error closing browser: {str(e)}")

    except Exception as e:
        logger.error(f"Error in download_images: {str(e)}")
        logger.error(f"Stack trace: {traceback.format_exc()}")
        if driver:
            try:
                driver.quit()
            except:
                pass
        return {
            "status": "error",
            "error": str(e),
            "downloaded": len(downloaded_files),
            "files": downloaded_files
        }

if __name__ == "__main__":
    try:
        logger.info("Starting MCP server...")
        mcp.run()
    except KeyboardInterrupt:
        logger.info("Server shutdown requested")
    except Exception as e:
        logger.error(f"Server error: {str(e)}")
        logger.error(f"Stack trace: {traceback.format_exc()}")
    finally:
        logger.info("Server shutdown complete")