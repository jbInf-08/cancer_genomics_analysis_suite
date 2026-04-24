# Local Kubernetes: minimal Helm run

This is the smallest path to exercise the chart on a one-node cluster without cloud wiring.

## Prereqs

- Docker
- A local cluster: [k3d](https://k3d.io/) (recommended) or [minikube](https://minikube.sigs.k8s.io/docs/start/) or [kind](https://kind.sigs.k8s.io/)
- [kubectl](https://kubernetes.io/docs/tasks/tools/) and [Helm 3](https://helm.sh/docs/intro/install/)

## 1) Start a cluster

k3d (creates a kubeconfig in your user profile):

```bash
k3d cluster create cgas-demo --port "8050:8050@loadbalancer"
export KUBECONFIG=$(k3d kubeconfig write cgas-demo)
```

minikube:

```bash
minikube start
```

## 2) Install the chart (dev values)

From the **repository root**:

```bash
helm install cgas ./CancerGenomicsSuite/helm/cancer-genomics-analysis-suite \
  --namespace cancer-genomics --create-namespace \
  -f ./CancerGenomicsSuite/helm/cancer-genomics-analysis-suite/values.yaml
```

For production-tuned sample overrides, compare with `values-production.yaml` and only promote settings you understand (ingress hosts, resource limits, secrets management).

## 3) Check pods

```bash
kubectl -n cancer-genomics get pods
kubectl -n cancer-genomics get svc
```

## 4) Uninstall

```bash
helm uninstall cgas -n cancer-genomics
```

If you used k3d: `k3d cluster delete cgas-demo`.

## Notes

- The chart can pull in many subsystems (Kafka, Neo4j, monitoring, etc. depending on values). For a **lighter** first install, start from `values.yaml` and scale dependencies down in your own `values-dev.yaml` rather than using production values on a laptop.
- Full cloud deployment, secrets, and CI/CD are covered in `docs/DEPLOYMENT_GUIDE.md` and `CancerGenomicsSuite/DEPLOYMENT_GUIDE.md`.
