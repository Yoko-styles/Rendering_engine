import json
import logging
import traceback
from pathlib import Path
from typing import Dict, Any, Tuple
import sys
import os


# Setup logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class SVGRenderer:
    """Standalone SVG rendering service"""
    
    def __init__(self, output_root: str = './temp_svg_render'):
        """Initialize the SVG renderer
        
        Args:
            output_root: Root directory for output files
        """
        self.output_root = Path(output_root)
        self.output_root.mkdir(parents=True, exist_ok=True)
        
        # Import required modules
        try:
            from assets.bodies.body_params import BodyParameters
            from assets.garment_programs.meta_garment import MetaGarment
            self.BodyParameters = BodyParameters
            self.MetaGarment = MetaGarment
            
            # # Load default body parameters
            body_path = Path(__file__).parent / 'assets' / 'bodies' / 'mean_all.yaml'
            if not body_path.exists():
                # Try alternative path relative to current working directory
                body_path = Path.cwd() / 'assets' / 'bodies' / 'mean_all.yaml'
            
            self.default_body_params = BodyParameters(body_path)
            logger.info("SVG Renderer initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize SVG Renderer: {str(e)}")
            raise

    def generate_svg_from_pattern_spec(self, 
                                     pattern_specification: Dict[str, Any], 
                                     session_dir: Path, 
                                     body_params=None,
                                     pattern_name: str = "rendered_pattern",
                                     with_text: bool = False, 
                                     view_ids: bool = False, 
                                     with_printable: bool = False) -> Tuple[Path, Path, Path, Path]:
        """Generate SVG from pattern specification JSON - Direct pattern loading like 3D endpoint"""
        try:
            # Setup body parameters
            if body_params:
                body = self.BodyParameters()
                body.load_from_dict(body_params)
            else:
                body = self.default_body_params
                
            # Save pattern specification to file in the correct format expected by VisPattern
            pattern_file = session_dir / f"{pattern_name}_specification.json"
            print(f"Saving pattern specification to: {pattern_file}")
            with open(pattern_file, 'w') as f:
                json.dump(pattern_specification, f, indent=2)
            
            # Load pattern directly using VisPattern (pass the file path to constructor)
            from pygarment.pattern.wrappers import VisPattern
            
            # Create VisPattern instance from the saved file
            pattern = VisPattern(str(pattern_file))
            pattern.name = pattern_name
            print("Session Directory:", str(session_dir))
            # Serialize to generate SVG files - directly in session_dir, no subfolder
            pattern_folder = pattern.serialize(
                str(session_dir),  # Ensure it's a string path
                to_subfolder=False,  # Don't create subfolder
                with_3d=False,  # Skip 3D generation for SVG-only
                with_text=with_text,
                view_ids=view_ids,
                with_printable=with_printable,
                empty_ok=True
            )
            pattern_folder = Path(pattern_folder)
            
            # DON'T save extra files - only SVG and PNG needed
            # body.save(pattern_folder)  # REMOVED
            
            # Clean up the temporary JSON file
            if pattern_file.exists():
                pattern_file.unlink()
            
            # Find generated files in the session directory
            svg_file = session_dir / f'{pattern_name}_pattern.svg'
            png_file = session_dir / f'{pattern_name}_pattern.png'
            pdf_file = session_dir / f'{pattern_name}_print_pattern.pdf' if with_printable else None
            
            # Clean up any files that might have been created in the current directory
            current_dir = Path.cwd()
            for cleanup_file in [f'{pattern_name}_pattern.svg', f'{pattern_name}_pattern.png']:
                cleanup_path = current_dir / cleanup_file
                if cleanup_path.exists() and cleanup_path != session_dir / cleanup_file:
                    cleanup_path.unlink()
                    logger.info(f"Cleaned up duplicate file: {cleanup_path}")
            
            return session_dir, svg_file, png_file, pdf_file
                
        except Exception as e:
            logger.error(f"Error generating SVG from pattern specification: {str(e)}")
            logger.error(traceback.format_exc())
            
            # Fallback: try to extract design parameters if available
            if 'design' in pattern_specification:
                logger.info("Falling back to design parameters extraction...")
                design_params = pattern_specification['design']
                return self._generate_svg_from_design_params(design_params, session_dir, body,
                                                           with_text, view_ids, with_printable)
            else:
                raise Exception(f"Could not process pattern specification: {str(e)}")

    def _generate_svg_from_design_params(self, 
                                       design_params: Dict[str, Any], 
                                       session_dir: Path, 
                                       body,
                                       with_text: bool, 
                                       view_ids: bool, 
                                       with_printable: bool) -> Tuple[Path, Path, Path, Path]:
        """Generate SVG from design parameters - fallback method"""
        try:
            # Create garment pattern using MetaGarment
            sew_pattern = self.MetaGarment('Fallback_Pattern', body, design_params)
            
            # Get the pattern assembly
            pattern = sew_pattern.assembly()
            
            # Serialize to generate SVG files - directly in session_dir, no subfolder
            pattern_folder = pattern.serialize(
                str(session_dir),  # Ensure it's a string path
                to_subfolder=False,  # Don't create subfolder
                with_3d=False,  # Skip 3D generation
                with_text=with_text,
                view_ids=view_ids,
                with_printable=with_printable,
                empty_ok=True
            )
            pattern_folder = Path(pattern_folder)
            
            # Find generated files in the session directory
            svg_file = session_dir / f'{sew_pattern.name}_pattern.svg'
            png_file = session_dir / f'{sew_pattern.name}_pattern.png'
            pdf_file = session_dir / f'{sew_pattern.name}_print_pattern.pdf' if with_printable else None
            
            return session_dir, svg_file, png_file, pdf_file
            
        except Exception as e:
            logger.error(f"Error generating SVG from design params: {str(e)}")
            raise

    def render_pattern(self, 
                      pattern_specification: Dict[str, Any],
                      session_id: str = None,
                      body_params: Dict[str, Any] = None,
                      pattern_name: str = "rendered_pattern",
                      with_text: bool = False,
                      view_ids: bool = False,
                      with_printable: bool = False) -> Dict[str, str]:
        """Main entry point for rendering patterns
        
        Args:
            pattern_specification: Pattern specification JSON
            session_id: Optional session ID (will generate if not provided)
            body_params: Optional body parameters
            pattern_name: Name for the pattern files
            with_text: Include text in SVG
            view_ids: Include view IDs in SVG
            with_printable: Generate printable PDF
            
        Returns:
            Dictionary with file paths and session info
        """
        if session_id is None:
            import uuid
            session_id = str(uuid.uuid4())
        
        # Create session directory
        session_dir = self.output_root / session_id
        session_dir.mkdir(parents=True, exist_ok=True)
        
        try:
            # Generate SVG files
            output_dir, svg_file, png_file, pdf_file = self.generate_svg_from_pattern_spec(
                pattern_specification=pattern_specification,
                session_dir=session_dir,
                body_params=body_params,
                pattern_name=pattern_name,
                with_text=with_text,
                view_ids=view_ids,
                with_printable=with_printable
            )
            
            return {
                'session_id': session_id,
                'output_dir': str(output_dir),
                'svg_file': str(svg_file),
                'png_file': str(png_file),
                'pdf_file': str(pdf_file) if pdf_file else None,
                'status': 'success'
            }
            
        except Exception as e:
            logger.error(f"Error in render_pattern: {str(e)}")
            return {
                'session_id': session_id,
                'status': 'error',
                'error': str(e)
            }


def main():
    """Example usage of the SVG renderer"""
    # Example pattern specification (you would replace this with actual data)
    # Load example pattern from file
    pattern_file = Path('/root/aipparel/Rendering_engine/assets/Patterns/dress_pencil_specification.json')
    if not pattern_file.exists():
        logger.error(f"Pattern file not found: {pattern_file}")
        sys.exit(1)
        
    try:
        with open(pattern_file, 'r') as f:
            example_pattern = json.load(f)
        logger.info(f"Successfully loaded pattern specification from {pattern_file}")
    except Exception as e:
        logger.error(f"Error loading pattern file: {str(e)}")
        sys.exit(1)
    # Initialize renderer
    renderer = SVGRenderer()
    
    # Render pattern
    result = renderer.render_pattern(
        pattern_specification=example_pattern,
        pattern_name="test_pattern",
        with_text=False,
        view_ids=False,
        with_printable=False
    )
    
    if result['status'] == 'success':
        print(f"✅ Pattern rendered successfully!")
        print(f"Session ID: {result['session_id']}")
        print(f"SVG File: {result['svg_file']}")
        print(f"PNG File: {result['png_file']}")
        if result['pdf_file']:
            print(f"PDF File: {result['pdf_file']}")
    else:
        print(f"❌ Error rendering pattern: {result['error']}")


if __name__ == "__main__":
    main()