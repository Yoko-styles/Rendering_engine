from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional, Dict, Any
import uuid
from pathlib import Path
import logging
import traceback
import sys

# Import your rendering engine classes
from rendering_engine import SVGRenderer, GarmentTo3DService, CombinedRenderingEngine

# Setup logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Pydantic models for requests and responses
class PatternRequest(BaseModel):
    pattern_specification: Optional[Dict[str, Any]] = None  # Direct pattern specification
    pattern: Optional[Dict[str, Any]] = None  # Wrapped pattern (from your JSON files)
    body_params: Optional[Dict[str, Any]] = None
    pattern_name: Optional[str] = "rendered_pattern"
    
    def get_pattern_data(self) -> Dict[str, Any]:
        """Extract pattern data regardless of format"""
        if self.pattern_specification is not None:
            return self.pattern_specification
        elif self.pattern is not None:
            return self.pattern
        else:
            raise ValueError("Either pattern_specification or pattern must be provided")

class SVGRequest(PatternRequest):
    with_text: bool = False
    view_ids: bool = False
    with_printable: bool = False

class SVGResponse(BaseModel):
    session_id: str
    svg_file_path: str
    png_file_path: str
    output_dir: str
    status: str

class Model3DResponse(BaseModel):
    session_id: str
    glb_file_path: str
    output_dir: str
    status: str

class CombinedResponse(BaseModel):
    session_id: str
    svg_result: Dict[str, Any]
    model_3d_result: Dict[str, Any]
    status: str

class SessionResponse(BaseModel):
    status: str
    message: str

# Initialize FastAPI app
app = FastAPI(
    title="Rendering Engine API",
    description="API for generating SVG patterns and 3D garment models",
    version="1.0.0"
)

# Initialize services
try:
    svg_service = SVGRenderer(output_root="./temp_svg_output")
    model_3d_service = GarmentTo3DService(output_root="./temp_3d_output") 
    combined_service = CombinedRenderingEngine(
        svg_output_root="./temp_svg_output",
        model_3d_output_root="./temp_3d_output"
    )
    logger.info("All rendering services initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize services: {str(e)}")
    logger.error(traceback.format_exc())
    raise

@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "service": "Rendering Engine API",
        "version": "1.0.0",
        "endpoints": {
            "svg_generation": "/generate_svg",
            "3d_generation": "/generate_3d", 
            "combined_generation": "/generate_both",
            "download_svg": "/download_svg/{session_id}",
            "download_png": "/download_png/{session_id}",
            "download_glb": "/download_glb/{session_id}",
            "cleanup": "/cleanup/{session_id}"
        }
    }

@app.post("/generate_svg", response_model=SVGResponse)
async def generate_svg_pattern(request: SVGRequest):
    """Generate SVG pattern files from pattern specification
    
    Args:
        request: SVGRequest containing pattern specification and options
        
    Returns:
        SVGResponse with session ID and file paths
    """
    try:
        logger.info("Received SVG generation request")
        
        # Extract pattern data regardless of format
        pattern_data = request.get_pattern_data()
        logger.debug(f"Pattern data keys: {list(pattern_data.keys())}")
        
        # The pattern_data should now be the complete JSON structure with properties
        # No need to wrap since we're sending pattern_specification directly
        pattern_specification = pattern_data
        
        # Generate unique session ID
        session_id = str(uuid.uuid4())
        logger.info(f"Created SVG session ID: {session_id}")
        
        # Generate SVG files
        logger.info("Starting SVG pattern rendering...")
        logger.debug(f"Pattern specification structure: {pattern_specification}")
        logger.debug(f"Pattern specification type: {type(pattern_specification)}")
        result = svg_service.render_pattern(
            pattern_specification=pattern_specification,
            session_id=session_id,
            body_params=request.body_params,
            pattern_name=request.pattern_name,
            with_text=request.with_text,
            view_ids=request.view_ids,
            with_printable=request.with_printable
        )
        
        if result['status'] == 'success':
            logger.info(f"SVG generation completed successfully")
            return SVGResponse(
                session_id=result['session_id'],
                svg_file_path=result['svg_file'],
                png_file_path=result['png_file'],
                output_dir=result['output_dir'],
                status=result['status']
            )
        else:
            logger.error(f"SVG generation failed: {result['error']}")
            raise HTTPException(status_code=500, detail=f"SVG generation failed: {result['error']}")
            
    except Exception as e:
        logger.error(f"Error in generate_svg_pattern: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Error in SVG generation: {str(e)}")

@app.post("/generate_3d", response_model=Model3DResponse)
async def generate_3d_model(request: PatternRequest):
    """Generate 3D model files from pattern specification
    
    Args:
        request: PatternRequest containing pattern specification
        
    Returns:
        Model3DResponse with session ID and file paths
    """
    try:
        logger.info("Received 3D model generation request")
        
        # Extract pattern data regardless of format
        pattern_data = request.get_pattern_data()
        logger.debug(f"Pattern data keys: {list(pattern_data.keys())}")
        
        # The pattern_data should now be the complete JSON structure with properties
        # No need to wrap since we're sending pattern_specification directly
        pattern_specification = pattern_data
        
        # Generate unique session ID
        session_id = str(uuid.uuid4())
        logger.info(f"Created 3D session ID: {session_id}")
        
        # Generate 3D model
        logger.info("Starting 3D model generation...")
        logger.debug(f"Pattern specification structure: {pattern_specification}")
        logger.debug(f"Pattern specification type: {type(pattern_specification)}")
        result = model_3d_service.generate_3d_model(
            pattern_specification=pattern_specification,
            session_id=session_id,
            body_params=request.body_params,
            pattern_name=request.pattern_name
        )
        
        if result['status'] == 'success':
            logger.info(f"3D model generation completed successfully")
            return Model3DResponse(
                session_id=result['session_id'],
                glb_file_path=result['glb_file'],
                output_dir=result['output_dir'],
                status=result['status']
            )
        else:
            logger.error(f"3D generation failed: {result['error']}")
            raise HTTPException(status_code=500, detail=f"3D generation failed: {result['error']}")
            
    except Exception as e:
        logger.error(f"Error in generate_3d_model: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Error in 3D generation: {str(e)}")

@app.post("/generate_both", response_model=CombinedResponse)
async def generate_both_formats(request: SVGRequest):
    """Generate both SVG and 3D files from the same pattern specification
    
    Args:
        request: SVGRequest containing pattern specification and options
        
    Returns:
        CombinedResponse with both SVG and 3D results
    """
    try:
        logger.info("Received combined generation request")
        
        # Extract pattern data regardless of format
        pattern_data = request.get_pattern_data()
        logger.debug(f"Pattern data keys: {list(pattern_data.keys())}")
        
        # The pattern_data should now be the complete JSON structure with properties
        # No need to wrap since we're sending pattern_specification directly
        pattern_specification = pattern_data
        
        # Generate unique session ID
        session_id = str(uuid.uuid4())
        logger.info(f"Created combined session ID: {session_id}")
        
        # Generate both SVG and 3D
        logger.info("Starting combined rendering...")
        result = combined_service.render_both(
            pattern_specification=pattern_specification,
            session_id=session_id,
            body_params=request.body_params,
            pattern_name=request.pattern_name,
            with_text=request.with_text,
            view_ids=request.view_ids,
            with_printable=request.with_printable
        )
        
        if result['status'] == 'success':
            logger.info(f"Combined generation completed successfully")
            return CombinedResponse(
                session_id=result['session_id'],
                svg_result=result['svg_result'],
                model_3d_result=result.get('3d_result', {}),  # Use .get() to avoid KeyError
                status=result['status']
            )
        else:
            logger.error(f"Combined generation failed: {result['error']}")
            raise HTTPException(status_code=500, detail=f"Combined generation failed: {result['error']}")
            
    except Exception as e:
        logger.error(f"Error in generate_both_formats: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Error in combined generation: {str(e)}")

@app.get("/download_svg/{session_id}")
async def download_svg_file(session_id: str):
    """Download the generated SVG file
    
    Args:
        session_id: Session ID from SVG generation request
        
    Returns:
        SVG file as attachment
    """
    try:
        logger.info(f"Received SVG download request for session: {session_id}")
        
        # Find the SVG file in the session directory
        session_dir = Path("./temp_svg_output") / session_id
        svg_files = list(session_dir.rglob("*.svg"))
        
        if not svg_files:
            logger.error(f"No SVG file found in session {session_id}")
            raise HTTPException(status_code=404, detail="SVG file not found")
            
        # Get the first SVG file (should be the pattern)
        svg_file = svg_files[0]
        logger.info(f"Returning SVG file: {svg_file}")
        
        return FileResponse(
            path=str(svg_file),
            filename=svg_file.name,
            media_type="image/svg+xml"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in download_svg_file: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/download_png/{session_id}")
async def download_png_file(session_id: str):
    """Download the generated PNG file
    
    Args:
        session_id: Session ID from SVG generation request
        
    Returns:
        PNG file as attachment
    """
    try:
        logger.info(f"Received PNG download request for session: {session_id}")
        
        # Find the PNG file in the session directory
        session_dir = Path("./temp_svg_output") / session_id
        png_files = list(session_dir.rglob("*.png"))
        
        if not png_files:
            logger.error(f"No PNG file found in session {session_id}")
            raise HTTPException(status_code=404, detail="PNG file not found")
            
        # Get the first PNG file (should be the pattern)
        png_file = png_files[0]
        logger.info(f"Returning PNG file: {png_file}")
        
        return FileResponse(
            path=str(png_file),
            filename=png_file.name,
            media_type="image/png"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in download_png_file: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/download_glb/{session_id}")
async def download_glb_file(session_id: str):
    """Download the generated GLB file
    
    Args:
        session_id: Session ID from 3D generation request
        
    Returns:
        GLB file as attachment
    """
    try:
        logger.info(f"Received GLB download request for session: {session_id}")
        
        # Find the GLB file in the session directory
        session_dir = Path("./temp_3d_output") / session_id
        glb_files = list(session_dir.rglob("*.glb"))
        
        if not glb_files:
            logger.error(f"No GLB file found in session {session_id}")
            raise HTTPException(status_code=404, detail="GLB file not found")
            
        # Get the first GLB file (should be the model)
        glb_file = glb_files[0]
        logger.info(f"Returning GLB file: {glb_file}")
        
        return FileResponse(
            path=str(glb_file),
            filename=glb_file.name,
            media_type="model/gltf-binary"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in download_glb_file: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/cleanup/{session_id}")
async def cleanup_session_files(session_id: str):
    """Clean up session files for both SVG and 3D outputs
    
    Args:
        session_id: Session to clean up
        
    Returns:
        SessionResponse with cleanup status
    """
    try:
        logger.info(f"Cleaning up session: {session_id}")
        
        # Clean up both SVG and 3D session directories
        svg_session_dir = Path("./temp_svg_output") / session_id
        model_3d_session_dir = Path("./temp_3d_output") / session_id
        
        cleaned_dirs = []
        
        if svg_session_dir.exists():
            import shutil
            shutil.rmtree(svg_session_dir)
            cleaned_dirs.append("SVG")
            
        if model_3d_session_dir.exists():
            import shutil
            shutil.rmtree(model_3d_session_dir)
            cleaned_dirs.append("3D")
        
        if cleaned_dirs:
            message = f"Session {session_id} cleaned up ({', '.join(cleaned_dirs)} directories)"
            logger.info(message)
            return SessionResponse(status="success", message=message)
        else:
            message = f"No files found for session {session_id}"
            logger.info(message)
            return SessionResponse(status="success", message=message)
            
    except Exception as e:
        logger.error(f"Error in cleanup_session_files: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "services": {
            "svg_renderer": "active",
            "3d_generator": "active", 
            "combined_engine": "active"
        }
    }

if __name__ == "__main__":
    import uvicorn
    print("🚀 Starting Rendering Engine API...")
    print("📄 SVG Generation: /generate_svg")
    print("🎯 3D Generation: /generate_3d")
    print("🔄 Combined Generation: /generate_both")
    print("📥 File Downloads: /download_svg/{session_id}, /download_png/{session_id}, /download_glb/{session_id}")
    print("🧹 Cleanup: /cleanup/{session_id}")
    print("📍 API Documentation: http://localhost:8000/docs")
    
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
