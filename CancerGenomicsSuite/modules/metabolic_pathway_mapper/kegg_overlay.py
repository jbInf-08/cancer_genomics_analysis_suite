"""
KEGG Pathway Overlay Module

This module provides integration with KEGG (Kyoto Encyclopedia of Genes and Genomes)
for pathway analysis and visualization.
"""

import requests
import json
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Any, Tuple
import logging
from pathlib import Path
import xml.etree.ElementTree as ET
import time

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class KEGGPathwayOverlay:
    """
    A class for integrating KEGG pathway data with metabolic pathway analysis.
    """
    
    def __init__(self, base_url: str = "https://rest.kegg.jp"):
        """
        Initialize the KEGG overlay.
        
        Args:
            base_url: Base URL for KEGG REST API
        """
        self.base_url = base_url
        self.cache_dir = Path("cache/kegg")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'CancerGenomicsSuite/1.0'
        })
        
    def get_pathway_list(self, organism: str = "hsa") -> List[Dict[str, str]]:
        """
        Get list of pathways for a specific organism.
        
        Args:
            organism: KEGG organism code (default: hsa for human)
            
        Returns:
            List of pathway dictionaries with id, name, and description
        """
        cache_file = self.cache_dir / f"pathways_{organism}.json"
        
        if cache_file.exists():
            with open(cache_file, 'r') as f:
                return json.load(f)
        
        try:
            url = f"{self.base_url}/list/pathway/{organism}"
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            
            pathways = []
            for line in response.text.strip().split('\n'):
                if line:
                    parts = line.split('\t')
                    if len(parts) >= 2:
                        pathway_id = parts[0].replace('path:', '')
                        pathway_name = parts[1]
                        description = parts[2] if len(parts) > 2 else ""
                        
                        pathways.append({
                            'id': pathway_id,
                            'name': pathway_name,
                            'description': description
                        })
            
            # Cache the results
            with open(cache_file, 'w') as f:
                json.dump(pathways, f, indent=2)
            
            logger.info(f"Retrieved {len(pathways)} pathways for organism {organism}")
            return pathways
            
        except Exception as e:
            logger.error(f"Error retrieving pathway list: {e}")
            return []
    
    def get_pathway_info(self, pathway_id: str) -> Dict[str, Any]:
        """
        Get detailed information about a specific pathway.
        
        Args:
            pathway_id: KEGG pathway ID (e.g., 'hsa00010')
            
        Returns:
            Dictionary containing pathway information
        """
        cache_file = self.cache_dir / f"pathway_{pathway_id}.json"
        
        if cache_file.exists():
            with open(cache_file, 'r') as f:
                return json.load(f)
        
        try:
            # Get pathway information
            url = f"{self.base_url}/get/{pathway_id}"
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            
            info = self._parse_pathway_info(response.text, pathway_id)
            
            # Cache the results
            with open(cache_file, 'w') as f:
                json.dump(info, f, indent=2)
            
            return info
            
        except Exception as e:
            logger.error(f"Error retrieving pathway info for {pathway_id}: {e}")
            return {}
    
    def get_pathway_genes(self, pathway_id: str) -> List[Dict[str, str]]:
        """
        Get genes associated with a pathway.
        
        Args:
            pathway_id: KEGG pathway ID
            
        Returns:
            List of gene dictionaries with id, name, and description
        """
        pathway_info = self.get_pathway_info(pathway_id)
        return pathway_info.get('genes', [])
    
    def get_pathway_compounds(self, pathway_id: str) -> List[Dict[str, str]]:
        """
        Get compounds/metabolites in a pathway.
        
        Args:
            pathway_id: KEGG pathway ID
            
        Returns:
            List of compound dictionaries
        """
        pathway_info = self.get_pathway_info(pathway_id)
        return pathway_info.get('compounds', [])
    
    def get_pathway_reactions(self, pathway_id: str) -> List[Dict[str, Any]]:
        """
        Get reactions in a pathway.
        
        Args:
            pathway_id: KEGG pathway ID
            
        Returns:
            List of reaction dictionaries
        """
        pathway_info = self.get_pathway_info(pathway_id)
        return pathway_info.get('reactions', [])
    
    def search_pathways(self, query: str, organism: str = "hsa") -> List[Dict[str, str]]:
        """
        Search for pathways by name or description.
        
        Args:
            query: Search query
            organism: KEGG organism code
            
        Returns:
            List of matching pathways
        """
        all_pathways = self.get_pathway_list(organism)
        query_lower = query.lower()
        
        matches = []
        for pathway in all_pathways:
            if (query_lower in pathway['name'].lower() or 
                query_lower in pathway['description'].lower()):
                matches.append(pathway)
        
        return matches
    
    def get_gene_pathway_mapping(self, organism: str = "hsa") -> Dict[str, List[str]]:
        """
        Get mapping of genes to pathways.
        
        Args:
            organism: KEGG organism code
            
        Returns:
            Dictionary mapping gene IDs to list of pathway IDs
        """
        cache_file = self.cache_dir / f"gene_pathway_mapping_{organism}.json"
        
        if cache_file.exists():
            with open(cache_file, 'r') as f:
                return json.load(f)
        
        try:
            url = f"{self.base_url}/link/pathway/{organism}"
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            
            mapping = {}
            for line in response.text.strip().split('\n'):
                if line:
                    parts = line.split('\t')
                    if len(parts) >= 2:
                        gene_id = parts[0].replace(f'{organism}:', '')
                        pathway_id = parts[1].replace('path:', '')
                        
                        if gene_id not in mapping:
                            mapping[gene_id] = []
                        mapping[gene_id].append(pathway_id)
            
            # Cache the results
            with open(cache_file, 'w') as f:
                json.dump(mapping, f, indent=2)
            
            logger.info(f"Retrieved gene-pathway mapping for {len(mapping)} genes")
            return mapping
            
        except Exception as e:
            logger.error(f"Error retrieving gene-pathway mapping: {e}")
            return {}
    
    def create_pathway_network(self, pathway_id: str) -> Dict[str, Any]:
        """
        Create a network representation of a KEGG pathway.
        
        Args:
            pathway_id: KEGG pathway ID
            
        Returns:
            Network representation with nodes and edges
        """
        pathway_info = self.get_pathway_info(pathway_id)
        
        if not pathway_info:
            return {}
        
        network = {
            'pathway_id': pathway_id,
            'pathway_name': pathway_info.get('name', ''),
            'nodes': [],
            'edges': []
        }
        
        # Add gene nodes
        for gene in pathway_info.get('genes', []):
            network['nodes'].append({
                'id': gene['id'],
                'name': gene['name'],
                'type': 'gene',
                'description': gene.get('description', '')
            })
        
        # Add compound nodes
        for compound in pathway_info.get('compounds', []):
            network['nodes'].append({
                'id': compound['id'],
                'name': compound['name'],
                'type': 'compound',
                'description': compound.get('description', '')
            })
        
        # Add reaction edges (simplified)
        for reaction in pathway_info.get('reactions', []):
            # This is a simplified representation
            # In reality, you'd need to parse the reaction details
            network['edges'].append({
                'source': reaction.get('substrates', []),
                'target': reaction.get('products', []),
                'reaction_id': reaction.get('id', ''),
                'type': 'reaction'
            })
        
        return network
    
    def overlay_expression_data(self, pathway_id: str, expression_data: pd.DataFrame) -> Dict[str, Any]:
        """
        Overlay gene expression data on a KEGG pathway.
        
        Args:
            pathway_id: KEGG pathway ID
            expression_data: DataFrame with gene expression data
            
        Returns:
            Dictionary with overlaid data
        """
        pathway_genes = self.get_pathway_genes(pathway_id)
        
        if not pathway_genes:
            return {}
        
        # Map KEGG gene IDs to expression data
        gene_mapping = {}
        for gene in pathway_genes:
            # Try to match gene names or IDs
            gene_name = gene['name'].split(',')[0].strip()  # Take first name
            matching_rows = expression_data[
                expression_data['gene_id'].str.contains(gene_name, case=False, na=False)
            ]
            
            if not matching_rows.empty:
                gene_mapping[gene['id']] = {
                    'kegg_info': gene,
                    'expression_data': matching_rows.iloc[0].to_dict()
                }
        
        # Calculate pathway-level statistics
        expression_values = []
        for gene_data in gene_mapping.values():
            expr_data = gene_data['expression_data']
            # Get numeric columns (assuming they're expression values)
            numeric_cols = [col for col in expr_data.keys() 
                          if isinstance(expr_data[col], (int, float))]
            if numeric_cols:
                expression_values.extend([expr_data[col] for col in numeric_cols])
        
        pathway_stats = {
            'mean_expression': np.mean(expression_values) if expression_values else 0,
            'std_expression': np.std(expression_values) if expression_values else 0,
            'num_genes_with_data': len(gene_mapping),
            'total_genes_in_pathway': len(pathway_genes)
        }
        
        return {
            'pathway_id': pathway_id,
            'pathway_stats': pathway_stats,
            'gene_mapping': gene_mapping,
            'overlay_success': len(gene_mapping) > 0
        }
    
    def _parse_pathway_info(self, text: str, pathway_id: str) -> Dict[str, Any]:
        """
        Parse KEGG pathway information from text response.
        
        Args:
            text: Raw text response from KEGG API
            pathway_id: Pathway ID
            
        Returns:
            Parsed pathway information
        """
        info = {
            'id': pathway_id,
            'name': '',
            'description': '',
            'genes': [],
            'compounds': [],
            'reactions': []
        }
        
        lines = text.split('\n')
        current_section = None
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            if line.startswith('NAME'):
                info['name'] = line.split('NAME')[1].strip()
            elif line.startswith('DESCRIPTION'):
                info['description'] = line.split('DESCRIPTION')[1].strip()
            elif line.startswith('GENE'):
                current_section = 'genes'
            elif line.startswith('COMPOUND'):
                current_section = 'compounds'
            elif line.startswith('REACTION'):
                current_section = 'reactions'
            elif line.startswith(' ') and current_section:
                # Parse gene/compound/reaction entries
                if current_section == 'genes':
                    gene_info = self._parse_gene_entry(line)
                    if gene_info:
                        info['genes'].append(gene_info)
                elif current_section == 'compounds':
                    compound_info = self._parse_compound_entry(line)
                    if compound_info:
                        info['compounds'].append(compound_info)
                elif current_section == 'reactions':
                    reaction_info = self._parse_reaction_entry(line)
                    if reaction_info:
                        info['reactions'].append(reaction_info)
        
        return info
    
    def _parse_gene_entry(self, line: str) -> Optional[Dict[str, str]]:
        """Parse a gene entry line."""
        try:
            parts = line.strip().split()
            if len(parts) >= 2:
                gene_id = parts[0]
                gene_name = parts[1]
                description = ' '.join(parts[2:]) if len(parts) > 2 else ''
                
                return {
                    'id': gene_id,
                    'name': gene_name,
                    'description': description
                }
        except Exception as e:
            logger.warning(f"Error parsing gene entry: {e}")
        return None
    
    def _parse_compound_entry(self, line: str) -> Optional[Dict[str, str]]:
        """Parse a compound entry line."""
        try:
            parts = line.strip().split()
            if len(parts) >= 2:
                compound_id = parts[0]
                compound_name = parts[1]
                description = ' '.join(parts[2:]) if len(parts) > 2 else ''
                
                return {
                    'id': compound_id,
                    'name': compound_name,
                    'description': description
                }
        except Exception as e:
            logger.warning(f"Error parsing compound entry: {e}")
        return None
    
    def _parse_reaction_entry(self, line: str) -> Optional[Dict[str, str]]:
        """Parse a reaction entry line."""
        try:
            parts = line.strip().split()
            if len(parts) >= 1:
                reaction_id = parts[0]
                description = ' '.join(parts[1:]) if len(parts) > 1 else ''
                
                return {
                    'id': reaction_id,
                    'description': description
                }
        except Exception as e:
            logger.warning(f"Error parsing reaction entry: {e}")
        return None
    
    def get_common_pathways(self, gene_list: List[str], organism: str = "hsa") -> Dict[str, List[str]]:
        """
        Find common pathways for a list of genes.
        
        Args:
            gene_list: List of gene names/IDs
            organism: KEGG organism code
            
        Returns:
            Dictionary mapping pathway IDs to lists of genes
        """
        gene_pathway_mapping = self.get_gene_pathway_mapping(organism)
        pathway_genes = {}
        
        for gene in gene_list:
            # Try to find matching gene in KEGG
            for kegg_gene, pathways in gene_pathway_mapping.items():
                if (gene.lower() in kegg_gene.lower() or 
                    kegg_gene.lower() in gene.lower()):
                    
                    for pathway in pathways:
                        if pathway not in pathway_genes:
                            pathway_genes[pathway] = []
                        pathway_genes[pathway].append(gene)
        
        return pathway_genes
    
    def export_pathway_data(self, pathway_id: str, output_format: str = 'json') -> str:
        """
        Export pathway data in specified format.
        
        Args:
            pathway_id: KEGG pathway ID
            output_format: Export format ('json', 'csv', 'tsv')
            
        Returns:
            Exported data as string
        """
        pathway_info = self.get_pathway_info(pathway_id)
        
        if output_format == 'json':
            return json.dumps(pathway_info, indent=2)
        elif output_format in ['csv', 'tsv']:
            # Convert to tabular format
            delimiter = ',' if output_format == 'csv' else '\t'
            
            # Create gene table
            genes_df = pd.DataFrame(pathway_info.get('genes', []))
            compounds_df = pd.DataFrame(pathway_info.get('compounds', []))
            
            if not genes_df.empty:
                genes_str = genes_df.to_csv(sep=delimiter, index=False)
            else:
                genes_str = ""
            
            if not compounds_df.empty:
                compounds_str = compounds_df.to_csv(sep=delimiter, index=False)
            else:
                compounds_str = ""
            
            return f"Genes:\n{genes_str}\n\nCompounds:\n{compounds_str}"
        
        return ""


def main():
    """Main function for testing the KEGG overlay."""
    overlay = KEGGPathwayOverlay()
    
    # Test pathway list retrieval
    print("Testing pathway list retrieval...")
    pathways = overlay.get_pathway_list("hsa")
    print(f"Retrieved {len(pathways)} pathways")
    
    if pathways:
        # Test pathway info retrieval
        test_pathway = pathways[0]['id']
        print(f"\nTesting pathway info for {test_pathway}...")
        info = overlay.get_pathway_info(test_pathway)
        print(f"Pathway name: {info.get('name', 'N/A')}")
        print(f"Number of genes: {len(info.get('genes', []))}")
        print(f"Number of compounds: {len(info.get('compounds', []))}")


if __name__ == "__main__":
    main()
