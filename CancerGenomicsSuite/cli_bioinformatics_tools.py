#!/usr/bin/env python3
"""
CLI Support for Bioinformatics Tools

This module provides command-line interfaces for all the integrated bioinformatics tools.
"""

import argparse
import sys
import os
import json
import logging
from typing import Dict, List, Optional, Any

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import all the bioinformatics tool clients
from modules.galaxy_integration.galaxy_client import GalaxyClient
from modules.r_integration.r_client import RClient
from modules.matlab_integration.matlab_client import MATLABClient
from modules.pymol_integration.pymol_client import PyMOLClient
from modules.text_editors.editor_client import TextEditorClient
from modules.ape_editor.ape_client import APEClient
from modules.igv_integration.igv_client import IGVClient
from modules.gromacs_integration.gromacs_client import GROMACSClient
from modules.wgsim_tools.wgsim_client import WGSIMClient
from modules.neurosnap_integration.neurosnap_client import NeurosnapClient
from modules.tamarind_bio.tamarind_client import TamarindClient

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class BioinformaticsCLI:
    """Command-line interface for bioinformatics tools"""
    
    def __init__(self):
        """Initialize the CLI with all available tools"""
        self.tools = {
            'galaxy': GalaxyClient(),
            'r': RClient(),
            'matlab': MATLABClient(),
            'pymol': PyMOLClient(),
            'editors': TextEditorClient(),
            'ape': APEClient(),
            'igv': IGVClient(),
            'gromacs': GROMACSClient(),
            'wgsim': WGSIMClient(),
            'neurosnap': NeurosnapClient(),
            'tamarind': TamarindClient()
        }
    
    def list_tools(self):
        """List all available bioinformatics tools"""
        print("Available Bioinformatics Tools:")
        print("=" * 50)
        
        for tool_name, tool_client in self.tools.items():
            status = "✅ Available" if self._is_tool_available(tool_client) else "❌ Not Available"
            print(f"{tool_name.upper():<12} - {status}")
        
        print("\nUse 'python cli_bioinformatics_tools.py <tool> --help' for tool-specific help")
    
    def _is_tool_available(self, tool_client) -> bool:
        """Check if a tool is available"""
        if hasattr(tool_client, 'is_available'):
            return tool_client.is_available()
        return True
    
    def galaxy_cli(self, args):
        """Galaxy CLI commands"""
        parser = argparse.ArgumentParser(description='Galaxy Integration CLI')
        parser.add_argument('--url', default='https://usegalaxy.org', help='Galaxy URL')
        parser.add_argument('--api-key', help='Galaxy API key')
        parser.add_argument('--list-workflows', action='store_true', help='List available workflows')
        parser.add_argument('--list-tools', action='store_true', help='List available tools')
        
        parsed_args = parser.parse_args(args)
        
        client = GalaxyClient(parsed_args.url, parsed_args.api_key)
        
        if parsed_args.list_workflows:
            workflows = client.get_workflows()
            print(f"Found {len(workflows)} workflows:")
            for workflow in workflows:
                print(f"  - {workflow.name} (ID: {workflow.id})")
        
        if parsed_args.list_tools:
            tools = client.get_tools()
            print(f"Found {len(tools)} tools:")
            for tool in tools[:10]:  # Show first 10
                print(f"  - {tool.get('name', 'Unknown')}")
    
    def r_cli(self, args):
        """R CLI commands"""
        parser = argparse.ArgumentParser(description='R Integration CLI')
        parser.add_argument('--script', help='R script file to execute')
        parser.add_argument('--code', help='R code to execute')
        parser.add_argument('--install-package', help='Install R package')
        
        parsed_args = parser.parse_args(args)
        
        client = RClient()
        
        if parsed_args.script:
            with open(parsed_args.script, 'r') as f:
                r_code = f.read()
            result = client.execute_r_script(r_code)
            print("R Script Output:")
            print(result['output'])
            if result['stderr']:
                print("Messages:")
                print(result['stderr'])
        
        if parsed_args.code:
            result = client.execute_r_script(parsed_args.code)
            print("R Code Output:")
            print(result['output'])
        
        if parsed_args.install_package:
            success = client.install_package(parsed_args.install_package)
            if success:
                print(f"Package {parsed_args.install_package} installed successfully")
            else:
                print(f"Failed to install package {parsed_args.install_package}")
    
    def matlab_cli(self, args):
        """MATLAB CLI commands"""
        parser = argparse.ArgumentParser(description='MATLAB Integration CLI')
        parser.add_argument('--script', help='MATLAB script file to execute')
        parser.add_argument('--code', help='MATLAB code to execute')
        parser.add_argument('--version', action='store_true', help='Show MATLAB version')
        
        parsed_args = parser.parse_args(args)
        
        client = MATLABClient()
        
        if not client.is_available():
            print("MATLAB is not available")
            return
        
        if parsed_args.version:
            print(f"MATLAB Version: {client.get_version()}")
        
        if parsed_args.script:
            with open(parsed_args.script, 'r') as f:
                matlab_code = f.read()
            result = client.execute_matlab_script(matlab_code)
            print("MATLAB Script Output:")
            print(result['output'])
        
        if parsed_args.code:
            result = client.execute_matlab_script(parsed_args.code)
            print("MATLAB Code Output:")
            print(result['output'])
    
    def pymol_cli(self, args):
        """PyMOL CLI commands"""
        parser = argparse.ArgumentParser(description='PyMOL Integration CLI')
        parser.add_argument('--script', help='PyMOL script file to execute')
        parser.add_argument('--load', help='Load structure file')
        parser.add_argument('--fetch', help='Fetch structure from PDB')
        parser.add_argument('--version', action='store_true', help='Show PyMOL version')
        
        parsed_args = parser.parse_args(args)
        
        client = PyMOLClient()
        
        if not client.is_available():
            print("PyMOL is not available")
            return
        
        if parsed_args.version:
            print(f"PyMOL Version: {client.get_version()}")
        
        if parsed_args.load:
            result = client.load_structure(parsed_args.load)
            if result['success']:
                print(f"Structure loaded successfully: {parsed_args.load}")
            else:
                print(f"Failed to load structure: {result['error']}")
        
        if parsed_args.fetch:
            result = client.fetch_structure(parsed_args.fetch)
            if result['success']:
                print(f"Structure fetched successfully: {parsed_args.fetch}")
            else:
                print(f"Failed to fetch structure: {result['error']}")
        
        if parsed_args.script:
            with open(parsed_args.script, 'r') as f:
                pymol_commands = f.read()
            result = client.execute_pymol_script(pymol_commands)
            if result['success']:
                print("PyMOL script executed successfully")
            else:
                print(f"PyMOL script failed: {result['error']}")
    
    def editors_cli(self, args):
        """Text Editors CLI commands"""
        parser = argparse.ArgumentParser(description='Text Editors CLI')
        parser.add_argument('--list-editors', action='store_true', help='List available editors')
        parser.add_argument('--open', help='Open file with editor')
        parser.add_argument('--editor', default='nano', help='Editor to use')
        parser.add_argument('--line', type=int, help='Line number to jump to')
        
        parsed_args = parser.parse_args(args)
        
        client = TextEditorClient()
        
        if parsed_args.list_editors:
            editors = client.get_available_editors()
            print("Available editors:")
            for editor in editors:
                info = client.get_editor_info(editor)
                if info['success']:
                    print(f"  - {editor}: {info['info']['description']}")
        
        if parsed_args.open:
            result = client.open_file(parsed_args.open, parsed_args.editor, parsed_args.line)
            if result['success']:
                print(f"File opened successfully: {parsed_args.open}")
            else:
                print(f"Failed to open file: {result['error']}")
    
    def ape_cli(self, args):
        """APE CLI commands"""
        parser = argparse.ArgumentParser(description='A Plasmid Editor CLI')
        parser.add_argument('--create', help='Create new plasmid')
        parser.add_argument('--sequence', help='DNA sequence for plasmid')
        parser.add_argument('--load', help='Load plasmid from file')
        parser.add_argument('--find-sites', help='Find restriction sites in sequence')
        parser.add_argument('--design-primers', help='Design primers (format: start,end)')
        parser.add_argument('--export', help='Export plasmid (format: genbank,fasta,ape)')
        
        parsed_args = parser.parse_args(args)
        
        client = APEClient()
        
        if parsed_args.create and parsed_args.sequence:
            result = client.create_plasmid(parsed_args.create, parsed_args.sequence)
            if result['success']:
                print(f"Plasmid created: {result['plasmid_name']}")
            else:
                print(f"Failed to create plasmid: {result['error']}")
        
        if parsed_args.load:
            result = client.load_plasmid(parsed_args.load)
            if result['success']:
                data = result['plasmid_data']
                print(f"Plasmid loaded: {data.get('name', 'Unknown')}")
                print(f"Length: {len(data.get('sequence', ''))} bp")
            else:
                print(f"Failed to load plasmid: {result['error']}")
        
        if parsed_args.find_sites:
            result = client.find_restriction_sites(parsed_args.find_sites)
            if result['success']:
                print(f"Found {result['total_sites']} restriction sites")
                for site in result['sites'][:5]:  # Show first 5
                    print(f"  {site['enzyme']}: position {site['position']}")
            else:
                print(f"Failed to find restriction sites: {result['error']}")
        
        if parsed_args.design_primers:
            start, end = map(int, parsed_args.design_primers.split(','))
            # This would need a sequence input
            print("Primer design requires sequence input")
    
    def igv_cli(self, args):
        """IGV CLI commands"""
        parser = argparse.ArgumentParser(description='IGV Integration CLI')
        parser.add_argument('--load-genome', help='Load genome (e.g., hg38)')
        parser.add_argument('--load-track', help='Load data track file')
        parser.add_argument('--goto', help='Navigate to genomic locus')
        parser.add_argument('--snapshot', help='Take snapshot (output file)')
        
        parsed_args = parser.parse_args(args)
        
        client = IGVClient()
        
        if not client.is_available():
            print("IGV is not available")
            return
        
        if parsed_args.load_genome:
            result = client.load_genome(parsed_args.load_genome)
            if result['success']:
                print(f"Genome loaded: {parsed_args.load_genome}")
            else:
                print(f"Failed to load genome: {result['error']}")
        
        if parsed_args.load_track:
            result = client.load_track(parsed_args.load_track)
            if result['success']:
                print(f"Track loaded: {parsed_args.load_track}")
            else:
                print(f"Failed to load track: {result['error']}")
        
        if parsed_args.goto:
            result = client.goto_locus(parsed_args.goto)
            if result['success']:
                print(f"Navigated to: {parsed_args.goto}")
            else:
                print(f"Failed to navigate: {result['error']}")
    
    def gromacs_cli(self, args):
        """GROMACS CLI commands"""
        parser = argparse.ArgumentParser(description='GROMACS Integration CLI')
        parser.add_argument('--version', action='store_true', help='Show GROMACS version')
        parser.add_argument('--run-simulation', help='Run simulation (input files JSON)')
        
        parsed_args = parser.parse_args(args)
        
        client = GROMACSClient()
        
        if not client.is_available():
            print("GROMACS is not available")
            return
        
        if parsed_args.version:
            print(f"GROMACS Version: {client.get_version()}")
        
        if parsed_args.run_simulation:
            with open(parsed_args.run_simulation, 'r') as f:
                input_files = json.load(f)
            result = client.run_simulation(input_files, {})
            if result['success']:
                print("Simulation completed successfully")
            else:
                print(f"Simulation failed: {result['error']}")
    
    def wgsim_cli(self, args):
        """WGSIM CLI commands"""
        parser = argparse.ArgumentParser(description='WGSIM Tools CLI')
        parser.add_argument('--reference', help='Reference genome file')
        parser.add_argument('--output', help='Output prefix')
        parser.add_argument('--num-reads', type=int, default=1000000, help='Number of reads')
        parser.add_argument('--read-length', type=int, default=100, help='Read length')
        parser.add_argument('--tool', choices=['wgsim', 'dwgsim'], default='wgsim', help='Tool to use')
        
        parsed_args = parser.parse_args(args)
        
        client = WGSIMClient()
        
        if parsed_args.reference and parsed_args.output:
            result = client.simulate_reads(
                parsed_args.reference,
                parsed_args.output,
                parsed_args.num_reads,
                parsed_args.read_length,
                tool=parsed_args.tool
            )
            if result['success']:
                print(f"Read simulation completed using {parsed_args.tool}")
                print(f"Generated {parsed_args.num_reads} reads of length {parsed_args.read_length}")
            else:
                print(f"Read simulation failed: {result['error']}")
    
    def neurosnap_cli(self, args):
        """Neurosnap CLI commands"""
        parser = argparse.ArgumentParser(description='Neurosnap Integration CLI')
        parser.add_argument('--analyze', help='Analyze neural data file')
        parser.add_argument('--analysis-type', default='spike_detection', help='Analysis type')
        parser.add_argument('--version', action='store_true', help='Show Neurosnap version')
        
        parsed_args = parser.parse_args(args)
        
        client = NeurosnapClient()
        
        if not client.is_available():
            print("Neurosnap is not available")
            return
        
        if parsed_args.version:
            print(f"Neurosnap Version: {client.get_version()}")
        
        if parsed_args.analyze:
            result = client.analyze_neural_data(parsed_args.analyze, parsed_args.analysis_type)
            if result['success']:
                print(f"Analysis completed: {parsed_args.analysis_type}")
            else:
                print(f"Analysis failed: {result['error']}")
    
    def tamarind_cli(self, args):
        """Tamarind Bio CLI commands"""
        parser = argparse.ArgumentParser(description='Tamarind Bio CLI')
        parser.add_argument('--workflow', help='Workflow file to run')
        parser.add_argument('--input', help='Input data (JSON format)')
        parser.add_argument('--version', action='store_true', help='Show Tamarind version')
        
        parsed_args = parser.parse_args(args)
        
        client = TamarindClient()
        
        if not client.is_available():
            print("Tamarind Bio is not available")
            return
        
        if parsed_args.version:
            print(f"Tamarind Bio Version: {client.get_version()}")
        
        if parsed_args.workflow and parsed_args.input:
            with open(parsed_args.input, 'r') as f:
                input_data = json.load(f)
            result = client.run_workflow(parsed_args.workflow, input_data)
            if result['success']:
                print("Workflow completed successfully")
            else:
                print(f"Workflow failed: {result['error']}")

def main():
    """Main CLI entry point"""
    if len(sys.argv) < 2:
        cli = BioinformaticsCLI()
        cli.list_tools()
        return
    
    tool = sys.argv[1].lower()
    args = sys.argv[2:]
    
    cli = BioinformaticsCLI()
    
    if tool == 'galaxy':
        cli.galaxy_cli(args)
    elif tool == 'r':
        cli.r_cli(args)
    elif tool == 'matlab':
        cli.matlab_cli(args)
    elif tool == 'pymol':
        cli.pymol_cli(args)
    elif tool == 'editors':
        cli.editors_cli(args)
    elif tool == 'ape':
        cli.ape_cli(args)
    elif tool == 'igv':
        cli.igv_cli(args)
    elif tool == 'gromacs':
        cli.gromacs_cli(args)
    elif tool == 'wgsim':
        cli.wgsim_cli(args)
    elif tool == 'neurosnap':
        cli.neurosnap_cli(args)
    elif tool == 'tamarind':
        cli.tamarind_cli(args)
    else:
        print(f"Unknown tool: {tool}")
        cli.list_tools()

if __name__ == '__main__':
    main()
