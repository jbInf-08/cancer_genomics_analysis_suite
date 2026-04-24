#!/bin/bash
# Docker Push Script for Cancer Genomics Analysis Suite
# This script pushes Docker images to various registries

set -e

# Configuration
IMAGE_NAME="cancer-genomics-analysis-suite"
DEFAULT_REGISTRY="docker.io"
DEFAULT_USERNAME="${DOCKER_HUB_USERNAME:-your-username}"

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
Docker Push Script for Cancer Genomics Analysis Suite

Usage: $0 [OPTIONS]

OPTIONS:
    -t, --tag TAG           Tag for the Docker image (default: latest)
    -r, --registry REGISTRY Docker registry (default: docker.io)
    -u, --username USERNAME Docker Hub username (default: your-username)
    -a, --all-tags          Push all local tags
    -l, --latest            Push latest tag
    -d, --dry-run           Show what would be pushed without actually pushing
    -v, --verbose           Verbose output
    -h, --help              Show this help message

REGISTRIES:
    docker.io               Docker Hub (default)
    ghcr.io                 GitHub Container Registry
    quay.io                 Red Hat Quay
    custom                  Custom registry URL

EXAMPLES:
    $0                                    # Push latest tag to Docker Hub
    $0 -t v1.0.0 -p                       # Push version 1.0.0
    $0 -r ghcr.io -u myusername -t dev    # Push dev tag to GitHub Container Registry
    $0 -a                                 # Push all local tags
    $0 -d                                 # Dry run - show what would be pushed

ENVIRONMENT VARIABLES:
    DOCKER_HUB_USERNAME     Docker Hub username
    DOCKER_HUB_TOKEN        Docker Hub access token
    GITHUB_TOKEN            GitHub token for GHCR
    QUAY_TOKEN              Quay.io token

EOF
}

# Default values
TAG="latest"
REGISTRY="$DEFAULT_REGISTRY"
USERNAME="$DEFAULT_USERNAME"
ALL_TAGS=false
LATEST_ONLY=false
DRY_RUN=false
VERBOSE=false

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -t|--tag)
            TAG="$2"
            shift 2
            ;;
        -r|--registry)
            REGISTRY="$2"
            shift 2
            ;;
        -u|--username)
            USERNAME="$2"
            shift 2
            ;;
        -a|--all-tags)
            ALL_TAGS=true
            shift
            ;;
        -l|--latest)
            LATEST_ONLY=true
            shift
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

# Set repository name based on registry
case "$REGISTRY" in
    "docker.io")
        REPOSITORY="${USERNAME}/${IMAGE_NAME}"
        ;;
    "ghcr.io")
        REPOSITORY="${USERNAME}/${IMAGE_NAME}"
        ;;
    "quay.io")
        REPOSITORY="${USERNAME}/${IMAGE_NAME}"
        ;;
    *)
        REPOSITORY="${USERNAME}/${IMAGE_NAME}"
        ;;
esac

FULL_IMAGE_NAME="${REGISTRY}/${REPOSITORY}"

log_info "Docker Push Configuration:"
log_info "  Registry: ${REGISTRY}"
log_info "  Repository: ${REPOSITORY}"
log_info "  Username: ${USERNAME}"
log_info "  Tag: ${TAG}"
log_info "  All tags: ${ALL_TAGS}"
log_info "  Latest only: ${LATEST_ONLY}"
log_info "  Dry run: ${DRY_RUN}"

# Check if Docker is running
if ! docker info >/dev/null 2>&1; then
    log_error "Docker is not running. Please start Docker and try again."
    exit 1
fi

# Login to registry
login_to_registry() {
    local registry="$1"
    local username="$2"
    
    case "$registry" in
        "docker.io")
            if [[ -n "$DOCKER_HUB_TOKEN" ]]; then
                log_info "Logging in to Docker Hub..."
                echo "$DOCKER_HUB_TOKEN" | docker login --username "$username" --password-stdin
            else
                log_warning "DOCKER_HUB_TOKEN not set. Please run 'docker login' manually."
                return 1
            fi
            ;;
        "ghcr.io")
            if [[ -n "$GITHUB_TOKEN" ]]; then
                log_info "Logging in to GitHub Container Registry..."
                echo "$GITHUB_TOKEN" | docker login ghcr.io --username "$username" --password-stdin
            else
                log_warning "GITHUB_TOKEN not set. Please run 'docker login ghcr.io' manually."
                return 1
            fi
            ;;
        "quay.io")
            if [[ -n "$QUAY_TOKEN" ]]; then
                log_info "Logging in to Quay.io..."
                echo "$QUAY_TOKEN" | docker login quay.io --username "$username" --password-stdin
            else
                log_warning "QUAY_TOKEN not set. Please run 'docker login quay.io' manually."
                return 1
            fi
            ;;
        *)
            log_warning "Custom registry detected. Please ensure you're logged in."
            ;;
    esac
}

# Get list of tags to push
get_tags_to_push() {
    local tags=()
    
    if [[ "$ALL_TAGS" == "true" ]]; then
        # Get all local tags for the image
        tags=($(docker images --format "{{.Tag}}" "${IMAGE_NAME}" | grep -v "<none>"))
    elif [[ "$LATEST_ONLY" == "true" ]]; then
        tags=("latest")
    else
        tags=("$TAG")
    fi
    
    echo "${tags[@]}"
}

# Push single tag
push_tag() {
    local tag="$1"
    local full_image="${FULL_IMAGE_NAME}:${tag}"
    
    # Check if image exists locally
    if ! docker images --format "{{.Repository}}:{{.Tag}}" | grep -q "^${IMAGE_NAME}:${tag}$"; then
        log_warning "Image ${IMAGE_NAME}:${tag} not found locally. Skipping."
        return 1
    fi
    
    # Tag image for registry
    local registry_image="${FULL_IMAGE_NAME}:${tag}"
    log_info "Tagging ${IMAGE_NAME}:${tag} as ${registry_image}"
    
    if [[ "$DRY_RUN" == "false" ]]; then
        if ! docker tag "${IMAGE_NAME}:${tag}" "${registry_image}"; then
            log_error "Failed to tag image"
            return 1
        fi
    fi
    
    # Push image
    log_info "Pushing ${registry_image}..."
    
    if [[ "$DRY_RUN" == "true" ]]; then
        log_info "[DRY RUN] Would push: ${registry_image}"
        return 0
    fi
    
    if docker push "${registry_image}"; then
        log_success "Successfully pushed: ${registry_image}"
        return 0
    else
        log_error "Failed to push: ${registry_image}"
        return 1
    fi
}

# Main execution
main() {
    # Login to registry
    if [[ "$DRY_RUN" == "false" ]]; then
        if ! login_to_registry "$REGISTRY" "$USERNAME"; then
            log_error "Failed to login to registry"
            exit 1
        fi
    fi
    
    # Get tags to push
    local tags=($(get_tags_to_push))
    
    if [[ ${#tags[@]} -eq 0 ]]; then
        log_error "No tags found to push"
        exit 1
    fi
    
    log_info "Tags to push: ${tags[*]}"
    
    # Push each tag
    local success_count=0
    local total_count=${#tags[@]}
    
    for tag in "${tags[@]}"; do
        if push_tag "$tag"; then
            ((success_count++))
        fi
    done
    
    # Summary
    log_info "Push summary: ${success_count}/${total_count} tags pushed successfully"
    
    if [[ $success_count -eq $total_count ]]; then
        log_success "All tags pushed successfully!"
    else
        log_warning "Some tags failed to push"
        exit 1
    fi
}

# Run main function
main
