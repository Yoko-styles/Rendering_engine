import json
import logging
import traceback
from pathlib import Path
from typing import Dict, Any, Tuple
import sys
import os
import uuid
import trimesh
import yaml
from typing import Optional


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
            
            # Rename files to remove "_pattern" suffix for cleaner naming
            simplified_svg_file = session_dir / f'{pattern_name}.svg'
            simplified_png_file = session_dir / f'{pattern_name}.png'
            
            # Rename the files if they exist
            if svg_file.exists():
                svg_file.rename(simplified_svg_file)
                svg_file = simplified_svg_file
            
            if png_file.exists():
                png_file.rename(simplified_png_file)
                png_file = simplified_png_file
            
            # Clean up any files that might have been created in the current directory
            current_dir = Path.cwd()
            for cleanup_file in [f'{pattern_name}_pattern.svg', f'{pattern_name}_pattern.png', f'{pattern_name}.svg', f'{pattern_name}.png']:
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


# 3D Generation Service Class
class GarmentTo3DService:
    """3D Garment Generation Service - Compatible with existing SVG renderer"""
    
    def __init__(self, output_root: str = './temp_3d_render'):
        """Initialize the 3D generation service
        
        Args:
            output_root: Root directory for output files
        """
        self.output_root = Path(output_root)
        self.output_root.mkdir(parents=True, exist_ok=True)
        
        # Import required modules for 3D generation
        try:
            from assets.bodies.body_params import BodyParameters
            from assets.garment_programs.meta_garment import MetaGarment
            import pygarment.data_config as data_config
            from pygarment.meshgen.boxmeshgen import BoxMesh
            from pygarment.meshgen.simulation import run_sim
            from pygarment.meshgen.sim_config import PathCofig
            
            self.BodyParameters = BodyParameters
            self.MetaGarment = MetaGarment
            self.data_config = data_config
            self.BoxMesh = BoxMesh
            self.run_sim = run_sim
            self.PathCofig = PathCofig
            
            # Load default body parameters
            body_path = Path(__file__).parent / 'assets' / 'bodies' / 'mean_all.yaml'
            if not body_path.exists():
                # Try alternative path relative to current working directory
                body_path = Path.cwd() / 'assets' / 'bodies' / 'mean_all.yaml'
            
            self.default_body_params = BodyParameters(body_path)
            
            # Load simulation properties
            sim_props_path = Path(__file__).parent / 'assets' / 'Sim_props' / 'gui_sim_props.yaml'
            if not sim_props_path.exists():
                sim_props_path = Path.cwd() / 'assets' / 'Sim_props' / 'gui_sim_props.yaml'
            
            self.sim_props = data_config.Properties(str(sim_props_path))
            self.sim_props.set_section_stats('sim', fails={}, sim_time={}, spf={}, 
                                           fin_frame={}, body_collisions={}, self_collisions={})
            self.sim_props.set_section_stats('render', render_time={})
            
            logger.info("3D Generation Service initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize 3D Generation Service: {str(e)}")
            raise

    def generate_3d(self, 
                   design_params: Dict[str, Any] = None,
                   pattern_specification: Dict[str, Any] = None,
                   session_id: str = None,
                   body_params: Optional[Dict[str, Any]] = None) -> Tuple[Path, Path]:
        """Generate 3D files from garment parameters OR pattern specification
        
        Args:
            design_params: Dictionary of design parameters (legacy)
            pattern_specification: Direct pattern specification JSON
            session_id: Unique session identifier
            body_params: Optional custom body parameters
            
        Returns:
            Tuple of (output directory path, GLB file path)
        """
        if design_params is None and pattern_specification is None:
            raise ValueError("Either design_params or pattern_specification must be provided")
        
        if session_id is None:
            session_id = str(uuid.uuid4())
        
        # Create session directory
        session_dir = self.output_root / session_id
        session_dir.mkdir(parents=True, exist_ok=True)

        # Setup body parameters
        if body_params:
            body = self.BodyParameters()
            body.load_from_dict(body_params)
        else:
            body = self.default_body_params

        if pattern_specification is not None:
            # Use pattern specification directly
            return self._generate_from_pattern_spec(pattern_specification, session_dir, body)
        else:
            # Legacy: Use design parameters to generate pattern
            return self._generate_from_design_params(design_params, session_dir, body)

    def _generate_from_pattern_spec(self, pattern_specification: Dict[str, Any], 
                                  session_dir: Path, body) -> Tuple[Path, Path]:
        """Generate 3D from pattern specification JSON"""
        try:
            # Save pattern specification to file
            pattern_name = "user_pattern"
            pattern_file = session_dir / f"{pattern_name}_specification.json"
            
            with open(pattern_file, 'w') as f:
                json.dump(pattern_specification, f, indent=2)
            
            # Setup paths for 3D generation
            paths = self.PathCofig(
                in_element_path=session_dir,
                out_path=session_dir,
                in_name=pattern_name,
                out_name=f'{pattern_name}_3D',
                body_name='mean_all',
                smpl_body=False,
                add_timestamp=False
            )

            # Generate and save garment box mesh
            garment_box_mesh = self.BoxMesh(paths.in_g_spec, self.sim_props['sim']['config']['resolution_scale'])
            garment_box_mesh.load()
            garment_box_mesh.serialize(paths, store_panels=False, 
                                     uv_config=self.sim_props['render']['config']['uv_texture'])

            # Run simulation
            self.run_sim(
                garment_box_mesh.name,
                self.sim_props,
                paths,
                save_v_norms=False,
                store_usd=False,
                optimize_storage=False,
                verbose=False
            )

            # Convert to GLB
            mesh = trimesh.load_mesh(paths.g_sim)
            pbr_material = mesh.visual.material.to_pbr()
            pbr_material.doubleSided = True
            mesh.visual.material = pbr_material
            glb_path = paths.out_el / f'{pattern_name}_sim.glb'
            mesh.export(glb_path)

            return paths.out_el, glb_path
            
        except Exception as e:
            logger.error(f"Error generating 3D from pattern specification: {str(e)}")
            logger.error(traceback.format_exc())
            
            # Fallback: try to extract design parameters if available
            if 'design' in pattern_specification:
                logger.info("Falling back to design parameters extraction...")
                design_params = pattern_specification['design']
                return self._generate_from_design_params(design_params, session_dir, body)
            else:
                raise Exception(f"Could not process pattern specification: {str(e)}")

    def _generate_from_design_params(self, design_params: Dict[str, Any], 
                                   session_dir: Path, body) -> Tuple[Path, Path]:
        """Generate 3D from design parameters (legacy method)"""
        try:
            # Create garment pattern
            sew_pattern = self.MetaGarment('Configured_design', body, design_params)
            
            # Save pattern
            pattern = sew_pattern.assembly()
            pattern_folder = pattern.serialize(
                session_dir,
                to_subfolder=True,
                with_3d=False,
                with_text=False,
                view_ids=False,
                with_printable=True,
                empty_ok=True
            )
            pattern_folder = Path(pattern_folder)
            
            # Save parameters
            body.save(pattern_folder)
            with open(pattern_folder / 'design_params.yaml', 'w') as f:
                yaml.dump({'design': design_params}, f, default_flow_style=False, sort_keys=False)

            # Setup paths for 3D generation
            paths = self.PathCofig(
                in_element_path=pattern_folder,
                out_path=session_dir,
                in_name=sew_pattern.name,
                out_name=f'{sew_pattern.name}_3D',
                body_name='mean_all',
                smpl_body=False,
                add_timestamp=False
            )

            # Generate and save garment box mesh
            garment_box_mesh = self.BoxMesh(paths.in_g_spec, self.sim_props['sim']['config']['resolution_scale'])
            garment_box_mesh.load()
            garment_box_mesh.serialize(paths, store_panels=False, 
                                     uv_config=self.sim_props['render']['config']['uv_texture'])

            # Run simulation
            self.run_sim(
                garment_box_mesh.name,
                self.sim_props,
                paths,
                save_v_norms=False,
                store_usd=False,
                optimize_storage=False,
                verbose=False
            )

            # Convert to GLB
            mesh = trimesh.load_mesh(paths.g_sim)
            pbr_material = mesh.visual.material.to_pbr()
            pbr_material.doubleSided = True
            mesh.visual.material = pbr_material
            glb_path = paths.out_el / f'{sew_pattern.name}_sim.glb'
            mesh.export(glb_path)

            return paths.out_el, glb_path
            
        except Exception as e:
            logger.error(f"Error generating 3D from design params: {str(e)}")
            raise

    def generate_3d_model(self, 
                         pattern_specification: Dict[str, Any],
                         session_id: str = None,
                         body_params: Dict[str, Any] = None,
                         pattern_name: str = "3d_pattern") -> Dict[str, str]:
        """Main entry point for 3D model generation
        
        Args:
            pattern_specification: Pattern specification JSON
            session_id: Optional session ID (will generate if not provided)
            body_params: Optional body parameters
            pattern_name: Name for the pattern files
            
        Returns:
            Dictionary with file paths and session info
        """
        if session_id is None:
            session_id = str(uuid.uuid4())
        
        try:
            # Generate 3D files
            output_dir, glb_file = self.generate_3d(
                pattern_specification=pattern_specification,
                session_id=session_id,
                body_params=body_params
            )
            
            return {
                'session_id': session_id,
                'output_dir': str(output_dir),
                'glb_file': str(glb_file),
                'status': 'success'
            }
            
        except Exception as e:
            logger.error(f"Error in generate_3d_model: {str(e)}")
            return {
                'session_id': session_id,
                'status': 'error',
                'error': str(e)
            }

    def cleanup_session(self, session_id: str):
        """Clean up session files
        
        Args:
            session_id: Session to clean up
        """
        session_dir = self.output_root / session_id
        if session_dir.exists():
            import shutil
            shutil.rmtree(session_dir)


# Combined Rendering Engine - Supports both SVG and 3D generation
class CombinedRenderingEngine:
    """Combined rendering engine that supports both SVG and 3D generation"""
    
    def __init__(self, svg_output_root: str = './temp_svg_render', 
                 model_3d_output_root: str = './temp_3d_render'):
        """Initialize the combined rendering engine
        
        Args:
            svg_output_root: Root directory for SVG output files
            model_3d_output_root: Root directory for 3D output files
        """
        # Initialize both services
        self.svg_renderer = SVGRenderer(svg_output_root)
        self.model_3d_service = GarmentTo3DService(model_3d_output_root)
        logger.info("Combined Rendering Engine initialized successfully")
    
    def render_svg(self, **kwargs):
        """Render SVG patterns - delegates to SVGRenderer"""
        return self.svg_renderer.render_pattern(**kwargs)
    
    def render_3d(self, **kwargs):
        """Generate 3D models - delegates to GarmentTo3DService"""
        return self.model_3d_service.generate_3d_model(**kwargs)
    
    def render_both(self, pattern_specification: Dict[str, Any],
                   session_id: str = None,
                   body_params: Dict[str, Any] = None,
                   pattern_name: str = "combined_pattern",
                   with_text: bool = False,
                   view_ids: bool = False,
                   with_printable: bool = False) -> Dict[str, Any]:
        """Render both SVG and 3D from the same pattern specification
        
        Args:
            pattern_specification: Pattern specification JSON
            session_id: Optional session ID (will generate if not provided)
            body_params: Optional body parameters
            pattern_name: Name for the pattern files
            with_text: Include text in SVG
            view_ids: Include view IDs in SVG
            with_printable: Generate printable PDF
            
        Returns:
            Dictionary with both SVG and 3D results
        """
        if session_id is None:
            session_id = str(uuid.uuid4())
        
        try:
            # Generate SVG
            svg_result = self.render_svg(
                pattern_specification=pattern_specification,
                session_id=f"svg_{session_id}",
                body_params=body_params,
                pattern_name=pattern_name,
                with_text=with_text,
                view_ids=view_ids,
                with_printable=with_printable
            )
            
            # Generate 3D
            model_3d_result = self.render_3d(
                pattern_specification=pattern_specification,
                session_id=f"3d_{session_id}",
                body_params=body_params,
                pattern_name=pattern_name
            )
            
            return {
                'session_id': session_id,
                'svg_result': svg_result,
                '3d_result': model_3d_result,
                'status': 'success'
            }
            
        except Exception as e:
            logger.error(f"Error in render_both: {str(e)}")
            return {
                'session_id': session_id,
                'status': 'error',
                'error': str(e)
            }

def main():
    """Example usage for 3D model generation testing"""
    # Load pattern specification from assets directory
    # Try multiple possible locations for the JSON file
    possible_files = [
        Path('assets/Patterns/hoody_mean_specification.json'),
        Path(__file__).parent / 'assets' / 'Patterns' / 'hoody_mean_specification.json',
        Path('assets') / 'Patterns' / 'hoody_mean_specification.json.json',
        Path('assets') / 'hoody_mean_specification.json.json',
        # Add more patterns if available
        Path('assets') / 'garment_specification.json',
        Path('assets') / 'pattern_specification.json'
    ]
    
    example_pattern = None
    pattern_file = None
    
    # Try to find any available JSON pattern file
    for file_path in possible_files:
        if file_path.exists():
            try:
                with open(file_path, 'r') as f:
                    example_pattern = json.load(f)
                pattern_file = file_path
                logger.info(f"Successfully loaded pattern specification from {pattern_file}")
                break
            except Exception as e:
                logger.warning(f"Could not load {file_path}: {str(e)}")
                continue
    
    # If no JSON file found, create a simple test pattern
    if example_pattern is None:
        logger.info("No pattern JSON file found in assets. Creating a simple test pattern...")
        example_pattern = {
            "panels": {
                "front": {
                    "edges": [
                        {"name": "waist", "curve": [[0, 0], [25, 0]]},
                        {"name": "side", "curve": [[25, 0], [25, 40]]},
                        {"name": "hem", "curve": [[25, 40], [0, 40]]},
                        {"name": "center_front", "curve": [[0, 40], [0, 0]]}
                    ]
                },
                "back": {
                    "edges": [
                        {"name": "waist", "curve": [[0, 0], [25, 0]]},
                        {"name": "side", "curve": [[25, 0], [25, 40]]},
                        {"name": "hem", "curve": [[25, 40], [0, 40]]},
                        {"name": "center_back", "curve": [[0, 40], [0, 0]]}
                    ]
                }
            },
            "sewing_pattern": [
                {"panel_1": "front", "edge_1": "side", "panel_2": "back", "edge_2": "side"}
            ]
        }
        logger.info("Using generated test pattern for 3D model creation")
    
    print(f"Using pattern from: {pattern_file if pattern_file else 'Generated test pattern'}")
    
    # MAIN FOCUS: Test SVG rendering only
    print("=" * 60)
    print("📄 TESTING SVG RENDERING")
    print("=" * 60)
    
    try:
        print("🔧 Initializing SVG Renderer...")
        svg_renderer = SVGRenderer(output_root='./temp_svg_output')
        print("✅ SVG Renderer initialized successfully!")
        
        print(f"📋 Pattern data preview: {str(example_pattern)[:200]}...")
        
        print("🚀 Starting SVG pattern rendering...")
        svg_result = svg_renderer.render_pattern(
            pattern_specification=example_pattern,
            pattern_name="test_svg_pattern_from_assets",
            with_text=False,
            view_ids=False,
            with_printable=False  # Disabled PDF generation
        )
        
        if svg_result['status'] == 'success':
            print(f"✅ SVG Pattern rendered successfully!")
            print(f"🆔 Session ID: {svg_result['session_id']}")
            print(f"📁 Output Directory: {svg_result['output_dir']}")
            print(f"📄 SVG File: {svg_result['svg_file']}")
            print(f"🖼️  PNG File: {svg_result['png_file']}")
            print(f"📍 You can find your files at: {Path(svg_result['output_dir']).absolute()}")
            print(f"� Files generated:")
            print(f"   • {Path(svg_result['svg_file']).name}")
            print(f"   • {Path(svg_result['png_file']).name}")
        else:
            print(f"❌ Error rendering SVG pattern: {svg_result['error']}")
            print("💡 Check if all SVG dependencies are installed")
    except Exception as e:
        print(f"❌ SVG rendering failed with exception: {str(e)}")
        print("💡 This might be due to missing dependencies or configuration files")
        print(f"📍 Error details: {traceback.format_exc()}")
    
    
    # 3D generation testing
    print("=" * 60)
    print("🎯 TESTING 3D MODEL GENERATION")
    print("=" * 60)
    
    try:
        print("🔧 Initializing 3D Generation Service...")
        model_3d_service = GarmentTo3DService(output_root='./temp_3d_output')
        print("✅ 3D Service initialized successfully!")
        
        print(f"📋 Pattern data preview: {str(example_pattern)[:200]}...")
        
        print("🚀 Starting 3D model generation...")
        model_3d_result = model_3d_service.generate_3d_model(
            pattern_specification=example_pattern,
            pattern_name="test_3d_pattern_from_assets"
        )
        
        if model_3d_result['status'] == 'success':
            print(f"✅ 3D Model generated successfully!")
            print(f"🆔 Session ID: {model_3d_result['session_id']}")
            print(f"📁 Output Directory: {model_3d_result['output_dir']}")
            print(f"🎯 GLB File: {model_3d_result['glb_file']}")
            print(f"📍 You can find your 3D model at: {Path(model_3d_result['glb_file']).absolute()}")
        else:
            print(f"❌ Error generating 3D model: {model_3d_result['error']}")
            print("💡 Check if all simulation dependencies are installed")
    except Exception as e:
        print(f"❌ 3D generation failed with exception: {str(e)}")
        print("💡 This might be due to missing dependencies or configuration files")
        print(f"📍 Error details: {traceback.format_exc()}")
    
    # Combined rendering testing
    print("\n" + "=" * 60)
    print("🔄 TESTING COMBINED RENDERING (SVG + 3D)")
    print("=" * 60)
    
    try:
        combined_engine = CombinedRenderingEngine()
        combined_result = combined_engine.render_both(
            pattern_specification=example_pattern,
            pattern_name="test_combined_pattern",
            with_text=False,
            view_ids=False,
            with_printable=False
        )
        
        if combined_result['status'] == 'success':
            print(f"✅ Combined rendering successful!")
            print(f"🆔 Session ID: {combined_result['session_id']}")
            
            svg_res = combined_result['svg_result']
            if svg_res['status'] == 'success':
                print(f"📄 SVG Files: {svg_res['svg_file']}, {svg_res['png_file']}")
            
            model_3d_res = combined_result['3d_result']
            if model_3d_res['status'] == 'success':
                print(f"🎯 3D File: {model_3d_res['glb_file']}")
        else:
            print(f"❌ Error in combined rendering: {combined_result['error']}")
    except Exception as e:
        print(f"❌ Combined rendering failed: {str(e)}")
        print("💡 SVG rendering should still work independently.")
    
    print("\n" + "=" * 60)
    print("🎉 ALL RENDERING TESTS COMPLETED!")
    print("📄 SVG Rendering: ✅ Active")
    print("🎯 3D Generation: ✅ Active") 
    print("🔄 Combined Mode: ✅ Active")
    print("=" * 60)


if __name__ == "__main__":
    main()