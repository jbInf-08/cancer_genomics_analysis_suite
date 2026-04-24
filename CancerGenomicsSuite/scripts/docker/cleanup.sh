#!/bin/bash
# Docker Cleanup Script for Cancer Genomics Analysis Suite
# This script cleans up Docker images, containers, and volumes

set -e

# Configuration
IMAGE_NAME="cancer-genomics-analysis-suite"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

show_help() {
    cat << EOF
Docker Cleanup Script for Cancer Genomics Analysis Suite

Usage: $0 [OPTIONS]

OPTIONS:
    -i, --images           Clean up Docker images
    -c, --containers       Clean up Docker containers
    -v, --volumes          Clean up Docker volumes
    -n, --networks         Clean up Docker networks
    -a, --all              Clean up everything
    -f, --force            Force cleanup without confirmation
    -k, --keep-tags TAGS   Keep specified tags (comma-separated)
    -d, --dry-run          Show what would be cleaned up
    -v, --verbose          Verbose output
    -h, --help             Show this help message

EXAMPLES:
    $0 -i                  # Clean up images only
    $0 -c -v               # Clean up containers and volumes
    $0 -a -f               # Clean up everything without confirmation
    $0 -i -k "latest,dev"  # Clean up images but keep latest and dev tags
    $0 -d                  # Dry run - show what would be cleaned up

EOF
}

# Default values
CLEAN_IMAGES=false
CLEAN_CONTAINERS=false
CLEAN_VOLUMES=false
CLEAN_NETWORKS=false
CLEAN_ALL=false
FORCE=false
KEEP_TAGS=""
DRY_RUN=false
VERBOSE=false

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -i|--images)
            CLEAN_IMAGES=true
            shift
            ;;
        -c|--containers)
            CLEAN_CONTAINERS=true
            shift
            ;;
        -v|--volumes)
            CLEAN_VOLUMES=true
            shift
            ;;
        -n|--networks)
            CLEAN_NETWORKS=true
            shift
            ;;
        -a|--all)
            CLEAN_ALL=true
            shift
            ;;
        -f|--force)
            FORCE=true
            shift
            ;;
        -k|--keep-tags)
            KEEP_TAGS="$2"
            shift 2
            ;;
        -d|--dry-run)
            DRY_RUN=true
            shift
            ;;
        -v|--verbose)
            VERBOSE=true
            shift
            ;;
        -h|--help)
            show_help
            exit 0
            ;;
        *)
            log_error "Unknown option: $1"
            show_help
            exit 1
            ;;
    esac
done

# If --all is specified, enable all cleanup options
if [[ "$CLEAN_ALL" == "true" ]]; then
    CLEAN_IMAGES=true
    CLEAN_CONTAINERS=true
    CLEAN_VOLUMES=true
    CLEAN_NETWORKS=true
fi

# If no options specified, show help
if [[ "$CLEAN_IMAGES" == "false" && "$CLEAN_CONTAINERS" == "false" && "$CLEAN_VOLUMES" == "false" && "$CLEAN_NETWORKS" == "false" ]]; then
    show_help
    exit 0
fi

# Check if Docker is running
if ! docker info >/dev/null 2>&1; then
    log_error "Docker is not running. Please start Docker and try again."
    exit 1
fi

# Confirmation prompt
confirm_cleanup() {
    if [[ "$FORCE" == "true" ]]; then
        return 0
    fi
    
    echo -n "Are you sure you want to proceed? (y/N): "
    read -r response
    if [[ "$response" =~ ^[Yy]$ ]]; then
        return 0
    else
        log_info "Cleanup cancelled"
        exit 0
    fi
}

# Clean up images
cleanup_images() {
    log_info "Cleaning up Docker images..."
    
    # Get list of images to remove
    local images_to_remove=()
    
    if [[ -n "$KEEP_TAGS" ]]; then
        # Keep specified tags
        IFS=',' read -ra KEEP_ARRAY <<< "$KEEP_TAGS"
        local keep_pattern=""
        for tag in "${KEEP_ARRAY[@]}"; do
            keep_pattern="${keep_pattern}|${tag}"
        done
        keep_pattern="${keep_pattern#|}"  # Remove leading |
        
        # Get images to remove (excluding kept tags)
        images_to_remove=($(docker images "${IMAGE_NAME}" --format "{{.Repository}}:{{.Tag}}" | grep -vE "(${keep_pattern})" || true))
    else
        # Remove all images for this project
        images_to_remove=($(docker images "${IMAGE_NAME}" --format "{{.Repository}}:{{.Tag}}" || true))
    fi
    
    if [[ ${#images_to_remove[@]} -eq 0 ]]; then
        log_info "No images to remove"
        return 0
    fi
    
    log_info "Images to remove:"
    for image in "${images_to_remove[@]}"; do
        echo "  - ${image}"
    done
    
    if [[ "$DRY_RUN" == "true" ]]; then
        log_info "[DRY RUN] Would remove ${#images_to_remove[@]} images"
        return 0
    fi
    
    if ! confirm_cleanup; then
        return 1
    fi
    
    # Remove images
    for image in "${images_to_remove[@]}"; do
        log_info "Removing image: ${image}"
        if docker rmi "$image" 2>/dev/null; then
            log_success "Removed: ${image}"
        else
            log_warning "Failed to remove: ${image} (may be in use)"
        fi
    done
    
    # Remove dangling images
    log_info "Removing dangling images..."
    local dangling_count=$(docker images -f "dangling=true" -q | wc -l)
    if [[ $dangling_count -gt 0 ]]; then
        if docker image prune -f; then
            log_success "Removed ${dangling_count} dangling images"
        else
            log_warning "Failed to remove some dangling images"
        fi
    else
        log_info "No dangling images found"
    fi
}

# Clean up containers
cleanup_containers() {
    log_info "Cleaning up Docker containers..."
    
    # Get list of stopped containers
    local stopped_containers=($(docker ps -a --filter "ancestor=${IMAGE_NAME}" --format "{{.ID}}" || true))
    
    if [[ ${#stopped_containers[@]} -eq 0 ]]; then
        log_info "No stopped containers to remove"
    else
        log_info "Stopped containers to remove:"
        for container in "${stopped_containers[@]}"; do
            local container_info=$(docker ps -a --filter "id=${container}" --format "{{.Names}} ({{.Status}})")
            echo "  - ${container_info}"
        done
        
        if [[ "$DRY_RUN" == "true" ]]; then
            log_info "[DRY RUN] Would remove ${#stopped_containers[@]} containers"
        else
            if ! confirm_cleanup; then
                return 1
            fi
            
            # Remove containers
            for container in "${stopped_containers[@]}"; do
                log_info "Removing container: ${container}"
                if docker rm "$container"; then
                    log_success "Removed container: ${container}"
                else
                    log_warning "Failed to remove container: ${container}"
                fi
            done
        fi
    fi
    
    # Remove all stopped containers (not just project-specific)
    log_info "Removing all stopped containers..."
    local all_stopped=$(docker ps -a -q --filter "status=exited" | wc -l)
    if [[ $all_stopped -gt 0 ]]; then
        if [[ "$DRY_RUN" == "true" ]]; then
            log_info "[DRY RUN] Would remove ${all_stopped} stopped containers"
        else
            if docker container prune -f; then
                log_success "Removed ${all_stopped} stopped containers"
            else
                log_warning "Failed to remove some stopped containers"
            fi
        fi
    else
        log_info "No stopped containers found"
    fi
}

# Clean up volumes
cleanup_volumes() {
    log_info "Cleaning up Docker volumes..."
    
    # Get list of unused volumes
    local unused_volumes=($(docker volume ls -q --filter "dangling=true" || true))
    
    if [[ ${#unused_volumes[@]} -eq 0 ]]; then
        log_info "No unused volumes to remove"
    else
        log_info "Unused volumes to remove:"
        for volume in "${unused_volumes[@]}"; do
            echo "  - ${volume}"
        done
        
        if [[ "$DRY_RUN" == "true" ]]; then
            log_info "[DRY RUN] Would remove ${#unused_volumes[@]} volumes"
        else
            if ! confirm_cleanup; then
                return 1
            fi
            
            # Remove volumes
            for volume in "${unused_volumes[@]}"; do
                log_info "Removing volume: ${volume}"
                if docker volume rm "$volume"; then
                    log_success "Removed volume: ${volume}"
                else
                    log_warning "Failed to remove volume: ${volume}"
                fi
            done
        fi
    fi
    
    # Remove all unused volumes
    log_info "Removing all unused volumes..."
    if [[ "$DRY_RUN" == "true" ]]; then
        log_info "[DRY RUN] Would remove all unused volumes"
    else
        if docker volume prune -f; then
            log_success "Removed all unused volumes"
        else
            log_warning "Failed to remove some unused volumes"
        fi
    fi
}

# Clean up networks
cleanup_networks() {
    log_info "Cleaning up Docker networks..."
    
    # Get list of unused networks
    local unused_networks=($(docker network ls -q --filter "type=custom" || true))
    
    if [[ ${#unused_networks[@]} -eq 0 ]]; then
        log_info "No unused networks to remove"
    else
        log_info "Unused networks to remove:"
        for network in "${unused_networks[@]}"; do
            local network_info=$(docker network ls --filter "id=${network}" --format "{{.Name}} ({{.Driver}})")
            echo "  - ${network_info}"
        done
        
        if [[ "$DRY_RUN" == "true" ]]; then
            log_info "[DRY RUN] Would remove ${#unused_networks[@]} networks"
        else
            if ! confirm_cleanup; then
                return 1
            fi
            
            # Remove networks
            for network in "${unused_networks[@]}"; do
                log_info "Removing network: ${network}"
                if docker network rm "$network" 2>/dev/null; then
                    log_success "Removed network: ${network}"
                else
                    log_warning "Failed to remove network: ${network} (may be in use)"
                fi
            done
        fi
    fi
}

# Show Docker system information
show_system_info() {
    log_info "Docker system information:"
    
    # Images
    local image_count=$(docker images -q | wc -l)
    local image_size=$(docker images --format "table {{.Size}}" | tail -n +2 | awk '{sum+=$1} END {print sum}' || echo "0")
    log_info "  Images: ${image_count} (${image_size} total)"
    
    # Containers
    local container_count=$(docker ps -a -q | wc -l)
    local running_count=$(docker ps -q | wc -l)
    log_info "  Containers: ${container_count} total (${running_count} running)"
    
    # Volumes
    local volume_count=$(docker volume ls -q | wc -l)
    log_info "  Volumes: ${volume_count}"
    
    # Networks
    local network_count=$(docker network ls -q | wc -l)
    log_info "  Networks: ${network_count}"
    
    # Disk usage
    log_info "  Disk usage:"
    docker system df
}

# Main execution
main() {
    log_info "Docker Cleanup Script"
    log_info "===================="
    
    # Show current system info
    show_system_info
    echo
    
    # Clean up based on options
    if [[ "$CLEAN_IMAGES" == "true" ]]; then
        cleanup_images
        echo
    fi
    
    if [[ "$CLEAN_CONTAINERS" == "true" ]]; then
        cleanup_containers
        echo
    fi
    
    if [[ "$CLEAN_VOLUMES" == "true" ]]; then
        cleanup_volumes
        echo
    fi
    
    if [[ "$CLEAN_NETWORKS" == "true" ]]; then
        cleanup_networks
        echo
    fi
    
    # Show final system info
    log_info "Cleanup completed. Final system information:"
    show_system_info
    
    log_success "Docker cleanup completed successfully!"
}

# Run main function
main
