# Rendering Engine API Documentation

## Overview

The Rendering Engine API is a FastAPI-based service that generates SVG patterns and 3D garment models from pattern specifications. It supports three main generation modes: SVG-only, 3D-only, and combined generation.

## 🚀 Quick Start

### 1. Start the API Server
```bash
python api_rendering_service.py
```
The server will run on `http://localhost:8000`

### 2. Run Interactive Tests
```bash
python test_api.py
```
Choose from the interactive menu to test specific endpoints.

### 3. API Documentation
Visit `http://localhost:8000/docs` for Swagger UI documentation.

## 📋 API Endpoints

### Core Generation Endpoints

#### `POST /generate_svg`
Generate SVG pattern files from pattern specification.

**Request Body:**
```json
{
  "pattern_specification": {
    "pattern": {
      "panels": {...},
      "properties": {...}
    },
    "body": {...}
  },
  "pattern_name": "my_pattern",
  "with_text": false,
  "view_ids": false,
  "with_printable": false
}
```

**Response:**
```json
{
  "session_id": "uuid-string",
  "svg_file_path": "/path/to/file.svg",
  "png_file_path": "/path/to/file.png",
  "output_dir": "/path/to/output",
  "status": "success"
}
```

#### `POST /generate_3d`
Generate 3D model files from pattern specification.

**Request Body:**
```json
{
  "pattern_specification": {
    "pattern": {
      "panels": {...},
      "properties": {...}
    },
    "body": {...}
  },
  "pattern_name": "my_pattern"
}
```

**Response:**
```json
{
  "session_id": "uuid-string",
  "glb_file_path": "/path/to/file.glb",
  "output_dir": "/path/to/output",
  "status": "success"
}
```

#### `POST /generate_both`
Generate both SVG and 3D files from the same pattern specification.

**Request Body:**
```json
{
  "pattern_specification": {
    "pattern": {
      "panels": {...},
      "properties": {...}
    },
    "body": {...}
  },
  "pattern_name": "my_pattern",
  "with_text": false,
  "view_ids": false,
  "with_printable": false
}
```

**Response:**
```json
{
  "session_id": "uuid-string",
  "svg_result": {
    "status": "success",
    "svg_file": "/path/to/file.svg",
    "png_file": "/path/to/file.png"
  },
  "model_3d_result": {
    "status": "success",
    "glb_file": "/path/to/file.glb"
  },
  "status": "success"
}
```

### File Download Endpoints

#### `GET /download_svg/{session_id}`
Download the generated SVG file for a session.

#### `GET /download_png/{session_id}`
Download the generated PNG file for a session.

#### `GET /download_glb/{session_id}`
Download the generated GLB file for a session.

### Utility Endpoints

#### `GET /`
Get API information and available endpoints.

#### `GET /health`
Check API health status.

#### `DELETE /cleanup/{session_id}`
Clean up session files (both SVG and 3D outputs).

## 📝 Request Format

### Pattern Specification Structure
The API expects a complete pattern specification in the following format:

```json
{
  "pattern_specification": {
    "pattern": {
      "panels": {
        "panel_name": {
          "edges": [...],
          "vertices": [...]
        }
      },
      "properties": {
        "curvature": 30,
        "ease": [...],
        "material": {...}
      }
    },
    "body": {
      "measurements": {...}
    }
  }
}
```

### Optional Parameters

#### For SVG Generation:
- `with_text`: Include text labels (default: false)
- `view_ids`: Show vertex/edge IDs (default: false) 
- `with_printable`: Generate printable version (default: false)

#### For All Endpoints:
- `pattern_name`: Custom name for output files (default: "rendered_pattern")
- `body_params`: Additional body parameters (optional)

## 🧪 Interactive Test Script

The `test_api.py` script provides an interactive way to test the API endpoints.

### Features:
- **Interactive Menu**: Choose which endpoints to test
- **Health Check**: Verify API connectivity before testing
- **Pattern Loading**: Automatically loads test pattern from `assets/Patterns/dress_pencil_specification.json`
- **Debug Output**: Shows request structure and response details
- **No File Management**: Focuses on API testing without download/cleanup

### Test Options:
1. **SVG Generation only** - Test `/generate_svg` endpoint
2. **3D Generation only** - Test `/generate_3d` endpoint  
3. **Combined Generation** - Test `/generate_both` endpoint
4. **Test All** - Run all three tests sequentially

### Usage:
```bash
python test_api.py
```

Follow the interactive prompts to select your test scenario.

## 🛠️ Configuration

### Environment Setup:
- **API Base URL**: `http://localhost:8000` (configurable in test script)
- **Pattern File**: `assets/Patterns/dress_pencil_specification.json`
- **Output Directories**: 
  - SVG: `./temp_svg_output`
  - 3D: `./temp_3d_output`

### Timeouts:
- SVG Generation: 60 seconds
- 3D Generation: 120 seconds  
- Combined Generation: 180 seconds

## 📊 Response Codes

- `200` - Success
- `404` - File not found (downloads)
- `500` - Internal server error
- `422` - Validation error (invalid request format)

## 🔧 Troubleshooting

### Common Issues:

1. **API Not Responding**
   - Ensure the API server is running on port 8000
   - Check if another process is using the port

2. **Pattern File Not Found**
   - Verify the pattern file exists at `assets/Patterns/dress_pencil_specification.json`
   - Check file permissions

3. **Generation Timeout**
   - Complex patterns may take longer
   - Consider increasing timeout values
   - Check server logs for processing errors

4. **Missing Dependencies**
   - Ensure all required packages are installed
   - Check the rendering engine modules are available

### Debug Mode:
The API includes detailed logging. Check console output for:
- Request structure validation
- Pattern processing steps
- Error details and stack traces

## 📁 File Structure

```
Rendering_engine/
├── api_rendering_service.py    # FastAPI server
├── test_api.py                 # Interactive test script
├── rendering_engine.py         # Core rendering logic
├── assets/
│   └── Patterns/
│       └── dress_pencil_specification.json
├── temp_svg_output/            # SVG output directory
└── temp_3d_output/             # 3D output directory
```

## 🎯 Example Usage

### Python Client Example:
```python
import requests

# Load your pattern data
with open('pattern.json', 'r') as f:
    pattern_data = json.load(f)

# Generate SVG
response = requests.post('http://localhost:8000/generate_svg', json={
    'pattern_specification': pattern_data,
    'pattern_name': 'my_dress',
    'with_text': True
})

if response.status_code == 200:
    result = response.json()
    session_id = result['session_id']
    print(f"SVG generated: {result['svg_file_path']}")
    
    # Download the file
    svg_response = requests.get(f'http://localhost:8000/download_svg/{session_id}')
    with open('my_dress.svg', 'wb') as f:
        f.write(svg_response.content)
```

## 📞 Support

For issues or questions:
1. Check the API health endpoint: `GET /health`
2. Review server logs for detailed error information
3. Use the interactive test script to isolate issues
4. Verify your pattern specification format matches the expected structure
