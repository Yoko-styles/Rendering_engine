"""
    Run or Resume simulation of a pattern dataset with MayaPy standalone mode
    Note that this module is executed in Maya (or by mayapy)

    How to use: 
        * fill out system.json with approppriate paths 
        Running itself:
        ./datasim.py --data <dataset folder name> --minibatch <size>  --config <simulation_rendering_configuration.json>

"""
import argparse
import sys
import shutil
from pathlib import Path
import yaml
import trimesh
import json
from typing import Optional, Dict, Any

# My modules
import pygarment.data_config as data_config
import pygarment.meshgen.datasim_utils as sim

# Custom imports
from assets.garment_programs.meta_garment import MetaGarment
from assets.bodies.body_params import BodyParameters
import pygarment as pyg
from pygarment.meshgen.boxmeshgen import BoxMesh
from pygarment.meshgen.simulation import run_sim
from pygarment.meshgen.sim_config import PathCofig


def get_command_args():
    """command line arguments to control the run"""
    # https://stackoverflow.com/questions/40001892/reading-named-command-arguments
    parser = argparse.ArgumentParser()
    parser.add_argument('--data', '-d', help='name of dataset folder', type=str)
    parser.add_argument('--config', '-c', help='name of .json file with desired simulation&rendering config', type=str,
                        default=None)
    parser.add_argument('--minibatch', '-b', help='number of examples to simulate in this run', type=int, default=None)
    parser.add_argument('--default_body', action='store_true', help='run dataset on default body')
    parser.add_argument('--caching', action='store_true', help='cache intermediate simulation')
    parser.add_argument('--rewrite_config', action='store_true', help='cache intermediate simulation')

    args = parser.parse_args()
    print(args)

    return args

def gather_renders(out_data_path: Path, verbose=False):
    renders_path = out_data_path / 'renders'
    renders_path.mkdir(exist_ok=True)

    render_files = list(out_data_path.glob('**/*render*.png'))
    for file in render_files:
        try: 
            shutil.copy(str(file), str(renders_path))
        except shutil.SameFileError:
            if verbose:
                print(f'File {file} already exists')
            pass


class GarmentTo3DService:
    def __init__(self, output_root: str = './tmp_3d_service'):
        """Initialize the 3D generation service
        
        Args:
            output_root: Root directory for output files
        """
        self.output_root = Path(output_root)
        self.output_root.mkdir(parents=True, exist_ok=True)
        
        # Load default body parameters
        self.default_body_params = BodyParameters(Path.cwd() / 'assets/bodies/mean_all.yaml')
        
        # Load simulation properties
        self.sim_props = data_config.Properties('./assets/Sim_props/gui_sim_props.yaml')
        self.sim_props.set_section_stats('sim', fails={}, sim_time={}, spf={}, 
                                       fin_frame={}, body_collisions={}, self_collisions={})
        self.sim_props.set_section_stats('render', render_time={})

    def generate_3d(self, 
                   design_params: Dict[str, Any] = None,
                   pattern_specification: Dict[str, Any] = None,
                   session_id: str = None,
                   body_params: Optional[Dict[str, Any]] = None) -> tuple[Path, Path]:
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
        
        # Create session directory
        session_dir = self.output_root / session_id
        session_dir.mkdir(parents=True, exist_ok=True)

        # Setup body parameters
        if body_params:
            body = BodyParameters()
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
                                  session_dir: Path, body: BodyParameters) -> tuple[Path, Path]:
        """Generate 3D from pattern specification JSON"""
        # Save pattern specification to file
        pattern_name = "user_pattern"
        pattern_file = session_dir / f"{pattern_name}_specification.json"
        
        with open(pattern_file, 'w') as f:
            json.dump(pattern_specification, f, indent=2)
        
        # Setup paths for 3D generation
        paths = PathCofig(
            in_element_path=session_dir,
            out_path=session_dir,
            in_name=pattern_name,
            out_name=f'{pattern_name}_3D',
            body_name='mean_all',
            smpl_body=False,
            add_timestamp=False
        )

        # Generate and save garment box mesh
        garment_box_mesh = BoxMesh(paths.in_g_spec, self.sim_props['sim']['config']['resolution_scale'])
        garment_box_mesh.load()
        garment_box_mesh.serialize(paths, store_panels=False, 
                                 uv_config=self.sim_props['render']['config']['uv_texture'])

        # Run simulation
        run_sim(
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

    def _generate_from_design_params(self, design_params: Dict[str, Any], 
                                   session_dir: Path, body: BodyParameters) -> tuple[Path, Path]:
        """Generate 3D from design parameters (legacy method)"""
        # Create garment pattern
        sew_pattern = MetaGarment('Configured_design', body, design_params)
        
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
        paths = PathCofig(
            in_element_path=pattern_folder,
            out_path=session_dir,
            in_name=sew_pattern.name,
            out_name=f'{sew_pattern.name}_3D',
            body_name='mean_all',
            smpl_body=False,
            add_timestamp=False
        )

        # Generate and save garment box mesh
        garment_box_mesh = BoxMesh(paths.in_g_spec, self.sim_props['sim']['config']['resolution_scale'])
        garment_box_mesh.load()
        garment_box_mesh.serialize(paths, store_panels=False, 
                                 uv_config=self.sim_props['render']['config']['uv_texture'])

        # Run simulation
        run_sim(
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

    def cleanup_session(self, session_id: str):
        """Clean up session files
        
        Args:
            session_id: Session to clean up
        """
        session_dir = self.output_root / session_id
        if session_dir.exists():
            shutil.rmtree(session_dir)


if __name__ == "__main__":

    command_args = get_command_args()
    system_config = data_config.Properties('./system.json') 

    # ------ Dataset ------
    dataset = command_args.data
    datapath = Path(system_config['datasets_path']) / dataset
    init_dataset_file = datapath / 'dataset_properties.yaml'

    # Create dataset_file in correct folder (default_body or random_body)
    body_type = 'default_body' if command_args.default_body else 'random_body'
    datapath = datapath / body_type / 'data' # Overwrite datapath to specific body type

    output_path = Path(system_config['datasets_sim']) / dataset / body_type
    output_path.mkdir(parents=True, exist_ok=True) 
    dataset_file_body = output_path / f'dataset_properties_{body_type}.yaml'
    if not dataset_file_body.exists():
        shutil.copy(str(init_dataset_file), str(dataset_file_body))
    dataset_file = dataset_file_body

    props = data_config.Properties(dataset_file_body)
    if 'frozen' in props and props['frozen']: #Where is this set?
        # avoid accidential re-runs of data
        print('Warning: dataset is frozen, processing is skipped')
        sys.exit(0)

    # ------- Defining sim props -----
    props.set_basic(data_folder=dataset)  # in case data properties are from other dataset/folder, update info
    if command_args.config is not None:
        props.merge(
            Path(system_config['sim_configs_path']) / command_args.config, 
            re_write=command_args.rewrite_config)    # Re-write sim config only explicitly 

    # ----- Main loop ----------
    finished = sim.batch_sim(
        datapath, 
        output_path, 
        props,
        run_default_body=command_args.default_body,
        num_samples=command_args.minibatch,  # run in mini-batch if requested
        caching=command_args.caching, force_restart=False)

    # ----- Try and resim fails once -----
    if finished:
        # NOTE: Could be larger than a regular batch
        finished = sim.resim_fails(
            datapath, 
            output_path, 
            props,
            run_default_body=command_args.default_body,
            caching=command_args.caching)

    props.add_sys_info()   # Save system information
    props.serialize(dataset_file)

    # ------ Gather renders -------
    gather_renders(output_path)

    # -------- fin --------
    if finished:
        # finished processing the dataset
        print('Dataset processing finished')
        sys.exit(0)
    else:
        sys.exit(1)  # not finished dataset processing