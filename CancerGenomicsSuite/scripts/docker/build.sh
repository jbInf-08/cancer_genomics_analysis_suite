#!/bin/bash
# Docker Build Script for Cancer Genomics Analysis Suite
# This script builds Docker images for different environments

set -e

# Configuration
IMAGE_NAME="cancer-genomics-analysis-suite"
REGISTRY="docker.io"
USERNAME="${DOCKER_HUB_USERNAME:-your-username}"
REPOSITORY="${USERNAME}/${IMAGE_NAME}"

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
Docker Build Script for Cancer Genomics Analysis Suite

Usage: $0 [OPTIONS]

OPTIONS:
    -t, --tag TAG           Tag for the Docker image (default: latest)
    -r, --registry REGISTRY Docker registry (default: docker.io)
    -u, --username USERNAME Docker Hub username (default: your-username)
    -p, --push              Push image to registry after building
    -m, --multiarch         Build multi-architecture image (amd64, arm64)
    -c, --cache             Use build cache
    -n, --no-cache          Don't use build cache
    -v, --verbose           Verbose output
    -h, --help              Show this help message

EXAMPLES:
    $0                                    # Build with default settings
    $0 -t v1.0.0 -p                       # Build and push version 1.0.0
    $0 -m -p                              # Build multi-arch and push
    $0 -t dev -u myusername -p            # Build dev tag with custom username and push

ENVIRONMENT VARIABLES:
    DOCKER_HUB_USERNAME    Docker Hub username
    DOCKER_HUB_TOKEN       Docker Hub access token
    BUILD_DATE             Build date (auto-generated if not set)
    VCS_REF                Git commit hash (auto-generated if not set)
    VERSION                Version tag (auto-generated if not set)

EOF
}

# Default values
TAG="latest"
PUSH=false
MULTIARCH=false
USE_CACHE=true
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
            REPOSITORY="${USERNAME}/${IMAGE_NAME}"
            shift 2
            ;;
        -p|--push)
            PUSH=true
            shift
            ;;
        -m|--multiarch)
            MULTIARCH=true
            shift
            ;;
        -c|--cache)
            USE_CACHE=true
            shift
            ;;
        -n|--no-cache)
            USE_CACHE=false
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

# Set build arguments
BUILD_DATE="${BUILD_DATE:-$(date -u +'%Y-%m-%dT%H:%M:%SZ')}"
VCS_REF="${VCS_REF:-$(git rev-parse --short HEAD 2>/dev/null || echo 'unknown')}"
VERSION="${VERSION:-${TAG}}"

# Full image name
FULL_IMAGE_NAME="${REGISTRY}/${REPOSITORY}:${TAG}"

log_info "Building Docker image: ${FULL_IMAGE_NAME}"
log_info "Build date: ${BUILD_DATE}"
log_info "VCS ref: ${VCS_REF}"
log_info "Version: ${VERSION}"

# Check if Docker is running
if ! docker info >/dev/null 2>&1; then
    log_error "Docker is not running. Please start Docker and try again."
    exit 1
fi

# Check if we're in the right directory
if [[ ! -f "Dockerfile" ]]; then
    log_error "Dockerfile not found. Please run this script from the project root directory."
    exit 1
fi

# Build command
BUILD_CMD="docker build"

# Add build arguments
BUILD_CMD="${BUILD_CMD} --build-arg BUILD_DATE=${BUILD_DATE}"
BUILD_CMD="${BUILD_CMD} --build-arg VCS_REF=${VCS_REF}"
BUILD_CMD="${BUILD_CMD} --build-arg VERSION=${VERSION}"

# Add cache options
if [[ "$USE_CACHE" == "false" ]]; then
    BUILD_CMD="${BUILD_CMD} --no-cache"
fi

# Add verbose output
if [[ "$VERBOSE" == "true" ]]; then
    BUILD_CMD="${BUILD_CMD} --progress=plain"
fi

# Add multi-architecture support
if [[ "$MULTIARCH" == "true" ]]; then
    log_info "Building multi-architecture image (linux/amd64, linux/arm64)"
    
    # Check if buildx is available
    if ! docker buildx version >/dev/null 2>&1; then
        log_error "Docker buildx is not available. Please install Docker buildx or use single-arch build."
        exit 1
    fi
    
    # Create and use buildx builder if it doesn't exist
    if ! docker buildx inspect cancer-genomics-builder >/dev/null 2>&1; then
        log_info "Creating buildx builder: cancer-genomics-builder"
        docker buildx create --name cancer-genomics-builder --use
    else
        docker buildx use cancer-genomics-builder
    fi
    
    # Build multi-arch image
    BUILD_CMD="docker buildx build --platform linux/amd64,linux/arm64"
    BUILD_CMD="${BUILD_CMD} --build-arg BUILD_DATE=${BUILD_DATE}"
    BUILD_CMD="${BUILD_CMD} --build-arg VCS_REF=${VCS_REF}"
    BUILD_CMD="${BUILD_CMD} --build-arg VERSION=${VERSION}"
    
    if [[ "$USE_CACHE" == "true" ]]; then
        BUILD_CMD="${BUILD_CMD} --cache-from type=gha"
        BUILD_CMD="${BUILD_CMD} --cache-to type=gha,mode=max"
    fi
    
    if [[ "$PUSH" == "true" ]]; then
        BUILD_CMD="${BUILD_CMD} --push"
    else
        BUILD_CMD="${BUILD_CMD} --load"
    fi
    
    if [[ "$VERBOSE" == "true" ]]; then
        BUILD_CMD="${BUILD_CMD} --progress=plain"
    fi
fi

# Add tag
BUILD_CMD="${BUILD_CMD} -t ${FULL_IMAGE_NAME}"

# Add context
BUILD_CMD="${BUILD_CMD} ."

# Execute build
log_info "Executing: ${BUILD_CMD}"
if eval "${BUILD_CMD}"; then
    log_success "Docker image built successfully: ${FULL_IMAGE_NAME}"
else
    log_error "Docker build failed"
    exit 1
fi

# Push image if requested
if [[ "$PUSH" == "true" && "$MULTIARCH" == "false" ]]; then
    log_info "Pushing image to registry..."
    
    # Check if logged in to registry
    if [[ "$REGISTRY" == "docker.io" ]]; then
        if ! docker info | grep -q "Username: ${USERNAME}"; then
            log_warning "Not logged in to Docker Hub. Please run 'docker login' first."
            if [[ -n "$DOCKER_HUB_TOKEN" ]]; then
                log_info "Attempting to login with token..."
                echo "$DOCKER_HUB_TOKEN" | docker login --username "$USERNAME" --password-stdin
            else
                log_error "DOCKER_HUB_TOKEN not set. Please set it or run 'docker login' manually."
                exit 1
            fi
        fi
    fi
    
    if docker push "${FULL_IMAGE_NAME}"; then
        log_success "Image pushed successfully: ${FULL_IMAGE_NAME}"
    else
        log_error "Failed to push image"
        exit 1
    fi
fi

# Show image information
log_info "Image information:"
docker images "${FULL_IMAGE_NAME}" --format "table {{.Repository}}\t{{.Tag}}\t{{.Size}}\t{{.CreatedAt}}"

# Show image layers (if verbose)
if [[ "$VERBOSE" == "true" ]]; then
    log_info "Image layers:"
    docker history "${FULL_IMAGE_NAME}" --format "table {{.CreatedBy}}\t{{.Size}}"
fi

log_success "Build completed successfully!"
