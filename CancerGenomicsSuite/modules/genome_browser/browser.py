"""
Genome Browser Module

This module provides functionality for browsing and visualizing genomic data,
including sequence data, annotations, and comparative genomics features.
"""

import json
import logging
from typing import Dict, List, Optional, Tuple, Any
import requests
from dataclasses import dataclass
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class GenomicRegion:
    """Represents a genomic region with coordinates and metadata."""
    chromosome: str
    start: int
    end: int
    strand: str = "+"
    name: Optional[str] = None
    description: Optional[str] = None
    
    def __post_init__(self):
        """Validate genomic coordinates."""
        if self.start < 0 or self.end < 0:
            raise ValueError("Genomic coordinates must be non-negative")
        if self.start >= self.end:
            raise ValueError("Start position must be less than end position")
        if self.strand not in ["+", "-"]:
            raise ValueError("Strand must be '+' or '-'")


@dataclass
class GenomicFeature:
    """Represents a genomic feature (gene, exon, etc.)."""
    region: GenomicRegion
    feature_type: str
    attributes: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert feature to dictionary for serialization."""
        return {
            "chromosome": self.region.chromosome,
            "start": self.region.start,
            "end": self.region.end,
            "strand": self.region.strand,
            "name": self.region.name,
            "description": self.region.description,
            "feature_type": self.feature_type,
            "attributes": self.attributes
        }


class GenomeBrowser:
    """
    Main genome browser class for handling genomic data visualization and navigation.
    """
    
    def __init__(self, reference_genome: str = "hg38"):
        """
        Initialize the genome browser.
        
        Args:
            reference_genome: Reference genome assembly (e.g., 'hg38', 'hg19', 'mm10')
        """
        self.reference_genome = reference_genome
        self.current_region: Optional[GenomicRegion] = None
        self.features: List[GenomicFeature] = []
        self.tracks: Dict[str, List[GenomicFeature]] = {}
        
        # Supported reference genomes
        self.supported_genomes = {
            "hg38": "Human (GRCh38)",
            "hg19": "Human (GRCh37)",
            "mm10": "Mouse (GRCm38)",
            "mm9": "Mouse (NCBIM37)",
            "dm6": "Drosophila (BDGP6)",
            "ce11": "C. elegans (WBcel235)"
        }
        
        if reference_genome not in self.supported_genomes:
            logger.warning(f"Reference genome {reference_genome} not in supported list")
    
    def set_region(self, chromosome: str, start: int, end: int, 
                   strand: str = "+", name: Optional[str] = None) -> GenomicRegion:
        """
        Set the current genomic region to browse.
        
        Args:
            chromosome: Chromosome name
            start: Start position (0-based)
            end: End position (0-based)
            strand: Strand orientation
            name: Optional name for the region
            
        Returns:
            GenomicRegion object
        """
        try:
            self.current_region = GenomicRegion(
                chromosome=chromosome,
                start=start,
                end=end,
                strand=strand,
                name=name
            )
            logger.info(f"Set region: {chromosome}:{start}-{end} ({strand})")
            return self.current_region
        except ValueError as e:
            logger.error(f"Invalid genomic region: {e}")
            raise
    
    def add_feature(self, feature: GenomicFeature) -> None:
        """
        Add a genomic feature to the browser.
        
        Args:
            feature: GenomicFeature object to add
        """
        self.features.append(feature)
        logger.info(f"Added feature: {feature.feature_type} at {feature.region.chromosome}:{feature.region.start}-{feature.region.end}")

    def remove_features_by_attribute(self, key: str, value: Any) -> int:
        """
        Remove features whose ``attributes[key] == value``.

        Returns:
            Number of features removed.
        """
        before = len(self.features)
        self.features = [f for f in self.features if f.attributes.get(key) != value]
        removed = before - len(self.features)
        if removed:
            logger.info("Removed %s features where %s == %s", removed, key, value)
        return removed
    
    def add_track(self, track_name: str, features: List[GenomicFeature]) -> None:
        """
        Add a track of features to the browser.
        
        Args:
            track_name: Name of the track
            features: List of GenomicFeature objects
        """
        self.tracks[track_name] = features
        logger.info(f"Added track '{track_name}' with {len(features)} features")
    
    def get_features_in_region(self, region: Optional[GenomicRegion] = None) -> List[GenomicFeature]:
        """
        Get all features that overlap with the specified region.
        
        Args:
            region: GenomicRegion to search in (uses current region if None)
            
        Returns:
            List of overlapping GenomicFeature objects
        """
        if region is None:
            region = self.current_region
        
        if region is None:
            return []
        
        overlapping_features = []
        for feature in self.features:
            if self._features_overlap(feature.region, region):
                overlapping_features.append(feature)
        
        return overlapping_features
    
    def _features_overlap(self, region1: GenomicRegion, region2: GenomicRegion) -> bool:
        """
        Check if two genomic regions overlap.
        
        Args:
            region1: First genomic region
            region2: Second genomic region
            
        Returns:
            True if regions overlap, False otherwise
        """
        if region1.chromosome != region2.chromosome:
            return False
        
        return not (region1.end <= region2.start or region2.end <= region1.start)
    
    def zoom_in(self, factor: float = 2.0) -> Optional[GenomicRegion]:
        """
        Zoom in on the current region by reducing the region size.
        
        Args:
            factor: Zoom factor (default 2.0)
            
        Returns:
            New GenomicRegion or None if no current region
        """
        if self.current_region is None:
            logger.warning("No current region to zoom in on")
            return None
        
        center = (self.current_region.start + self.current_region.end) // 2
        current_size = self.current_region.end - self.current_region.start
        new_size = int(current_size / factor)
        
        new_start = max(0, center - new_size // 2)
        new_end = new_start + new_size
        
        self.current_region = GenomicRegion(
            chromosome=self.current_region.chromosome,
            start=new_start,
            end=new_end,
            strand=self.current_region.strand,
            name=self.current_region.name
        )
        
        logger.info(f"Zoomed in: {self.current_region.chromosome}:{self.current_region.start}-{self.current_region.end}")
        return self.current_region
    
    def zoom_out(self, factor: float = 2.0) -> Optional[GenomicRegion]:
        """
        Zoom out from the current region by increasing the region size.
        
        Args:
            factor: Zoom factor (default 2.0)
            
        Returns:
            New GenomicRegion or None if no current region
        """
        if self.current_region is None:
            logger.warning("No current region to zoom out from")
            return None
        
        center = (self.current_region.start + self.current_region.end) // 2
        current_size = self.current_region.end - self.current_region.start
        new_size = int(current_size * factor)
        
        new_start = max(0, center - new_size // 2)
        new_end = new_start + new_size
        
        self.current_region = GenomicRegion(
            chromosome=self.current_region.chromosome,
            start=new_start,
            end=new_end,
            strand=self.current_region.strand,
            name=self.current_region.name
        )
        
        logger.info(f"Zoomed out: {self.current_region.chromosome}:{self.current_region.start}-{self.current_region.end}")
        return self.current_region
    
    def pan_left(self, distance: int) -> Optional[GenomicRegion]:
        """
        Pan left (towards smaller coordinates) in the current region.
        
        Args:
            distance: Distance to pan in base pairs
            
        Returns:
            New GenomicRegion or None if no current region
        """
        if self.current_region is None:
            logger.warning("No current region to pan")
            return None
        
        region_size = self.current_region.end - self.current_region.start
        new_start = max(0, self.current_region.start - distance)
        new_end = new_start + region_size
        
        self.current_region = GenomicRegion(
            chromosome=self.current_region.chromosome,
            start=new_start,
            end=new_end,
            strand=self.current_region.strand,
            name=self.current_region.name
        )
        
        logger.info(f"Panned left: {self.current_region.chromosome}:{self.current_region.start}-{self.current_region.end}")
        return self.current_region
    
    def pan_right(self, distance: int) -> Optional[GenomicRegion]:
        """
        Pan right (towards larger coordinates) in the current region.
        
        Args:
            distance: Distance to pan in base pairs
            
        Returns:
            New GenomicRegion or None if no current region
        """
        if self.current_region is None:
            logger.warning("No current region to pan")
            return None
        
        region_size = self.current_region.end - self.current_region.start
        new_start = self.current_region.start + distance
        new_end = new_start + region_size
        
        self.current_region = GenomicRegion(
            chromosome=self.current_region.chromosome,
            start=new_start,
            end=new_end,
            strand=self.current_region.strand,
            name=self.current_region.name
        )
        
        logger.info(f"Panned right: {self.current_region.chromosome}:{self.current_region.start}-{self.current_region.end}")
        return self.current_region
    
    def search_features(self, query: str, feature_type: Optional[str] = None) -> List[GenomicFeature]:
        """
        Search for features by name or description.
        
        Args:
            query: Search query string
            feature_type: Optional filter by feature type
            
        Returns:
            List of matching GenomicFeature objects
        """
        query_lower = query.lower()
        matches = []
        
        for feature in self.features:
            # Check if feature type matches (if specified)
            if feature_type and feature.feature_type != feature_type:
                continue
            
            # Check name and description
            if (feature.region.name and query_lower in feature.region.name.lower()) or \
               (feature.region.description and query_lower in feature.region.description.lower()):
                matches.append(feature)
            
            # Check attributes
            for attr_value in feature.attributes.values():
                if isinstance(attr_value, str) and query_lower in attr_value.lower():
                    matches.append(feature)
                    break
        
        logger.info(f"Found {len(matches)} features matching '{query}'")
        return matches
    
    def export_region_data(self, format: str = "json") -> str:
        """
        Export current region and features data.
        
        Args:
            format: Export format ('json', 'gff3', 'bed')
            
        Returns:
            Exported data as string
        """
        if self.current_region is None:
            return ""
        
        region_features = self.get_features_in_region()
        
        if format == "json":
            data = {
                "reference_genome": self.reference_genome,
                "region": {
                    "chromosome": self.current_region.chromosome,
                    "start": self.current_region.start,
                    "end": self.current_region.end,
                    "strand": self.current_region.strand,
                    "name": self.current_region.name
                },
                "features": [feature.to_dict() for feature in region_features],
                "export_timestamp": datetime.now().isoformat()
            }
            return json.dumps(data, indent=2)
        
        elif format == "bed":
            bed_lines = []
            for feature in region_features:
                bed_line = f"{feature.region.chromosome}\t{feature.region.start}\t{feature.region.end}\t{feature.region.name or '.'}\t.\t{feature.region.strand}"
                bed_lines.append(bed_line)
            return "\n".join(bed_lines)
        
        elif format == "gff3":
            gff_lines = ["##gff-version 3"]
            gff_lines.append(f"##sequence-region {self.current_region.chromosome} {self.current_region.start} {self.current_region.end}")
            
            for feature in region_features:
                attrs = ";".join([f"{k}={v}" for k, v in feature.attributes.items()])
                gff_line = f"{feature.region.chromosome}\t.\t{feature.feature_type}\t{feature.region.start + 1}\t{feature.region.end}\t.\t{feature.region.strand}\t.\t{attrs}"
                gff_lines.append(gff_line)
            
            return "\n".join(gff_lines)
        
        else:
            raise ValueError(f"Unsupported export format: {format}")
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about the current browser state.
        
        Returns:
            Dictionary with browser statistics
        """
        stats = {
            "reference_genome": self.reference_genome,
            "total_features": len(self.features),
            "total_tracks": len(self.tracks),
            "current_region": None,
            "features_in_current_region": 0
        }
        
        if self.current_region:
            stats["current_region"] = {
                "chromosome": self.current_region.chromosome,
                "start": self.current_region.start,
                "end": self.current_region.end,
                "size": self.current_region.end - self.current_region.start
            }
            stats["features_in_current_region"] = len(self.get_features_in_region())
        
        # Feature type counts
        feature_types = {}
        for feature in self.features:
            feature_types[feature.feature_type] = feature_types.get(feature.feature_type, 0) + 1
        stats["feature_type_counts"] = feature_types
        
        return stats


class UCSCGenomeBrowser(GenomeBrowser):
    """
    Genome browser with UCSC Genome Browser integration.
    """
    
    def __init__(self, reference_genome: str = "hg38"):
        super().__init__(reference_genome)
        self.ucsc_base_url = "https://api.genome.ucsc.edu"
    
    def fetch_ucsc_track_data(self, track_name: str, region: Optional[GenomicRegion] = None) -> List[Dict[str, Any]]:
        """
        Fetch track data from UCSC Genome Browser API.
        
        Args:
            track_name: Name of the UCSC track
            region: Genomic region (uses current region if None)
            
        Returns:
            List of track data dictionaries
        """
        if region is None:
            region = self.current_region
        
        if region is None:
            logger.warning("No region specified for UCSC track fetch")
            return []
        
        try:
            url = f"{self.ucsc_base_url}/getData/track"
            params = {
                "genome": self.reference_genome,
                "track": track_name,
                "chrom": region.chromosome,
                "start": region.start,
                "end": region.end
            }
            
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            logger.info(f"Fetched {len(data.get('values', []))} items from UCSC track '{track_name}'")
            return data.get('values', [])
            
        except requests.RequestException as e:
            logger.error(f"Error fetching UCSC track data: {e}")
            return []
    
    def get_ucsc_tracks(self) -> List[str]:
        """
        Get list of available UCSC tracks for the current reference genome.
        
        Returns:
            List of available track names
        """
        try:
            url = f"{self.ucsc_base_url}/list/tracks"
            params = {"genome": self.reference_genome}
            
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            tracks = []
            for track_group in data.get('ucscGenomeBrowser', {}).get('tracks', []):
                tracks.extend(track_group.get('tracks', []))
            
            logger.info(f"Found {len(tracks)} UCSC tracks for {self.reference_genome}")
            return tracks
            
        except requests.RequestException as e:
            logger.error(f"Error fetching UCSC tracks: {e}")
            return []


def create_sample_genome_browser() -> GenomeBrowser:
    """
    Create a sample genome browser with example data.
    
    Returns:
        GenomeBrowser instance with sample data
    """
    browser = GenomeBrowser("hg38")
    
    # Set a sample region (BRCA1 gene region)
    browser.set_region("chr17", 43000000, 43100000, name="BRCA1 region")
    
    # Add some sample features
    sample_features = [
        GenomicFeature(
            region=GenomicRegion("chr17", 43044000, 43045000, name="BRCA1 exon 1"),
            feature_type="exon",
            attributes={"gene": "BRCA1", "transcript": "BRCA1-001", "exon_number": 1}
        ),
        GenomicFeature(
            region=GenomicRegion("chr17", 43050000, 43051000, name="BRCA1 exon 2"),
            feature_type="exon",
            attributes={"gene": "BRCA1", "transcript": "BRCA1-001", "exon_number": 2}
        ),
        GenomicFeature(
            region=GenomicRegion("chr17", 43044000, 43051000, name="BRCA1 gene"),
            feature_type="gene",
            attributes={"gene": "BRCA1", "biotype": "protein_coding", "description": "Breast cancer type 1 susceptibility protein"}
        )
    ]
    
    for feature in sample_features:
        browser.add_feature(feature)
    
    # Add a track
    browser.add_track("genes", [f for f in sample_features if f.feature_type == "gene"])
    browser.add_track("exons", [f for f in sample_features if f.feature_type == "exon"])
    
    return browser


if __name__ == "__main__":
    # Example usage
    browser = create_sample_genome_browser()
    
    print("Genome Browser Statistics:")
    stats = browser.get_statistics()
    for key, value in stats.items():
        print(f"  {key}: {value}")
    
    print("\nFeatures in current region:")
    features = browser.get_features_in_region()
    for feature in features:
        print(f"  {feature.feature_type}: {feature.region.name} ({feature.region.chromosome}:{feature.region.start}-{feature.region.end})")
    
    print("\nExporting region data (JSON):")
    print(browser.export_region_data("json"))
