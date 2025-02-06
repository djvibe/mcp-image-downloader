# DJVIBE MCP Image Downloader

A Python-based MCP server for downloading high-resolution images from Google Images.

## Setup

1. Install Python dependencies:
```bash
pip install -r requirements.txt
```

2. Ensure ChromeDriver is installed at:
```
D:\DJVIBE\TOOLS\chromedriver-win64\chromedriver.exe
```

## Running the Server

```bash
python server.py
```

## Directory Structure
```
D:\DJVIBE\MCP\mcp-image-downloader\
├── server.py          # Main MCP server implementation
├── requirements.txt   # Python dependencies
├── logs\             # Server logs
├── README.md         # Documentation
└── LICENSE           # License information
```

## Features
- High-resolution image downloads through Chrome
- Quality filtering with size verification (>180KB default)
- Safe file operations with temp file handling
- Headless browser support
- Error recovery and retry logic
- Clean browser session management

## Tool Usage
```python
{
    "command": "download_images",
    "args": {
        "query": "artist name live performance 2023",
        "num_images": 5,
        "min_size": 180,
        "image_type": "photo"
    }
}
```