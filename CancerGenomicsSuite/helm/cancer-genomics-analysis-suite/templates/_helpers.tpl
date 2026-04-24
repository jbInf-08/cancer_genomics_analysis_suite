{{/*
Expand the name of the chart.
*/}}
{{- define "cancer-genomics-analysis-suite.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create a default fully qualified app name.
We truncate at 63 chars because some Kubernetes name fields are limited to this (by the DNS naming spec).
If release name contains chart name it will be used as a full name.
*/}}
{{- define "cancer-genomics-analysis-suite.fullname" -}}
{{- if .Values.fullnameOverride }}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- $name := default .Chart.Name .Values.nameOverride }}
{{- if contains $name .Release.Name }}
{{- .Release.Name | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" }}
{{- end }}
{{- end }}
{{- end }}

{{/*
Create chart name and version as used by the chart label.
*/}}
{{- define "cancer-genomics-analysis-suite.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Common labels
*/}}
{{- define "cancer-genomics-analysis-suite.labels" -}}
helm.sh/chart: {{ include "cancer-genomics-analysis-suite.chart" . }}
{{ include "cancer-genomics-analysis-suite.selectorLabels" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{/*
Selector labels
*/}}
{{- define "cancer-genomics-analysis-suite.selectorLabels" -}}
app.kubernetes.io/name: {{ include "cancer-genomics-analysis-suite.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{/*
Create the name of the service account to use
*/}}
{{- define "cancer-genomics-analysis-suite.serviceAccountName" -}}
{{- if .Values.serviceAccount.create }}
{{- default (include "cancer-genomics-analysis-suite.fullname" .) .Values.serviceAccount.name }}
{{- else }}
{{- default "default" .Values.serviceAccount.name }}
{{- end }}
{{- end }}

{{/*
Create the name of the secret to use
*/}}
{{- define "cancer-genomics-analysis-suite.secretName" -}}
{{- if .Values.secrets.app.create }}
{{- printf "%s-secrets" (include "cancer-genomics-analysis-suite.fullname" .) }}
{{- else }}
{{- .Values.secrets.app.name }}
{{- end }}
{{- end }}

{{/*
PostgreSQL fullname
*/}}
{{- define "cancer-genomics-analysis-suite.postgresql.fullname" -}}
{{- if .Values.postgresql.enabled }}
{{- printf "%s-postgresql" (include "cancer-genomics-analysis-suite.fullname" .) }}
{{- else }}
{{- .Values.externalDatabase.host }}
{{- end }}
{{- end }}

{{/*
PostgreSQL secret name
*/}}
{{- define "cancer-genomics-analysis-suite.postgresql.secretName" -}}
{{- if .Values.postgresql.enabled }}
{{- printf "%s-postgresql" (include "cancer-genomics-analysis-suite.fullname" .) }}
{{- else }}
{{- .Values.externalDatabase.existingSecret }}
{{- end }}
{{- end }}

{{/*
Redis fullname
*/}}
{{- define "cancer-genomics-analysis-suite.redis.fullname" -}}
{{- if .Values.redis.enabled }}
{{- printf "%s-redis" (include "cancer-genomics-analysis-suite.fullname" .) }}
{{- else }}
{{- .Values.externalRedis.host }}
{{- end }}
{{- end }}

{{/*
Redis secret name
*/}}
{{- define "cancer-genomics-analysis-suite.redis.secretName" -}}
{{- if .Values.redis.enabled }}
{{- printf "%s-redis" (include "cancer-genomics-analysis-suite.fullname" .) }}
{{- else }}
{{- .Values.externalRedis.existingSecret }}
{{- end }}
{{- end }}

{{/*
Image name
*/}}
{{- define "cancer-genomics-analysis-suite.image" -}}
{{- $registry := .Values.image.registry | default .Values.global.imageRegistry -}}
{{- if $registry }}
{{- printf "%s/%s:%s" $registry .Values.image.repository (.Values.image.tag | default .Chart.AppVersion) }}
{{- else }}
{{- printf "%s:%s" .Values.image.repository (.Values.image.tag | default .Chart.AppVersion) }}
{{- end }}
{{- end }}

{{/*
Web image name
*/}}
{{- define "cancer-genomics-analysis-suite.web.image" -}}
{{- $registry := .Values.web.image.registry | default .Values.image.registry | default .Values.global.imageRegistry -}}
{{- if $registry }}
{{- printf "%s/%s:%s" $registry .Values.web.image.repository (.Values.web.image.tag | default .Values.image.tag | default .Chart.AppVersion) }}
{{- else }}
{{- printf "%s:%s" .Values.web.image.repository (.Values.web.image.tag | default .Values.image.tag | default .Chart.AppVersion) }}
{{- end }}
{{- end }}

{{/*
Celery image name
*/}}
{{- define "cancer-genomics-analysis-suite.celery.image" -}}
{{- $registry := .Values.celery.worker.image.registry | default .Values.image.registry | default .Values.global.imageRegistry -}}
{{- if $registry }}
{{- printf "%s/%s:%s" $registry .Values.celery.worker.image.repository (.Values.celery.worker.image.tag | default .Values.image.tag | default .Chart.AppVersion) }}
{{- else }}
{{- printf "%s:%s" .Values.celery.worker.image.repository (.Values.celery.worker.image.tag | default .Values.image.tag | default .Chart.AppVersion) }}
{{- end }}
{{- end }}

{{/*
Nginx image name
*/}}
{{- define "cancer-genomics-analysis-suite.nginx.image" -}}
{{- $registry := .Values.nginx.image.registry | default .Values.global.imageRegistry -}}
{{- if $registry }}
{{- printf "%s/%s:%s" $registry .Values.nginx.image.repository .Values.nginx.image.tag }}
{{- else }}
{{- printf "%s:%s" .Values.nginx.image.repository .Values.nginx.image.tag }}
{{- end }}
{{- end }}

{{/*
Environment variables
*/}}
{{- define "cancer-genomics-analysis-suite.env" -}}
- name: FLASK_ENV
  value: {{ .Values.config.app.environment | quote }}
- name: LOG_LEVEL
  value: {{ .Values.config.app.debug | ternary "DEBUG" "INFO" | quote }}
- name: DATABASE_HOST
  value: {{ include "cancer-genomics-analysis-suite.postgresql.fullname" . | quote }}
- name: DATABASE_PORT
  value: "5432"
- name: DATABASE_NAME
  value: {{ .Values.config.database.name | quote }}
- name: DATABASE_USER
  value: {{ .Values.config.database.user | quote }}
- name: DATABASE_PASSWORD
  valueFrom:
    secretKeyRef:
      name: {{ include "cancer-genomics-analysis-suite.postgresql.secretName" . }}
      key: postgres-password
- name: REDIS_HOST
  value: {{ include "cancer-genomics-analysis-suite.redis.fullname" . }}-master
- name: REDIS_PORT
  value: "6379"
- name: CELERY_BROKER_URL
  value: {{ .Values.config.celery.broker_url | quote }}
- name: CELERY_RESULT_BACKEND
  value: {{ .Values.config.celery.result_backend | quote }}
- name: SECRET_KEY
  valueFrom:
    secretKeyRef:
      name: {{ include "cancer-genomics-analysis-suite.secretName" . }}
      key: secret-key
- name: JWT_SECRET_KEY
  valueFrom:
    secretKeyRef:
      name: {{ include "cancer-genomics-analysis-suite.secretName" . }}
      key: jwt-secret-key
{{- end }}

{{/*
Pod disruption budget
*/}}
{{- define "cancer-genomics-analysis-suite.podDisruptionBudget" -}}
{{- if .Values.podDisruptionBudget.enabled }}
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: {{ include "cancer-genomics-analysis-suite.fullname" . }}
  labels:
    {{- include "cancer-genomics-analysis-suite.labels" . | nindent 4 }}
spec:
  {{- if .Values.podDisruptionBudget.minAvailable }}
  minAvailable: {{ .Values.podDisruptionBudget.minAvailable }}
  {{- end }}
  {{- if .Values.podDisruptionBudget.maxUnavailable }}
  maxUnavailable: {{ .Values.podDisruptionBudget.maxUnavailable }}
  {{- end }}
  selector:
    matchLabels:
      {{- include "cancer-genomics-analysis-suite.selectorLabels" . | nindent 6 }}
{{- end }}
{{- end }}

{{/*
Network policy
*/}}
{{- define "cancer-genomics-analysis-suite.networkPolicy" -}}
{{- if .Values.networkPolicy.enabled }}
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: {{ include "cancer-genomics-analysis-suite.fullname" . }}
  labels:
    {{- include "cancer-genomics-analysis-suite.labels" . | nindent 4 }}
spec:
  podSelector:
    matchLabels:
      {{- include "cancer-genomics-analysis-suite.selectorLabels" . | nindent 6 }}
  policyTypes:
    - Ingress
    - Egress
  {{- with .Values.networkPolicy.ingress }}
  ingress:
    {{- toYaml . | nindent 4 }}
  {{- end }}
  {{- with .Values.networkPolicy.egress }}
  egress:
    {{- toYaml . | nindent 4 }}
  {{- end }}
{{- end }}
{{- end }}
