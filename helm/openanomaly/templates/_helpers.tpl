{{/*
Expand the name of the chart.
*/}}
{{- define "openanomaly.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create a default fully qualified app name.
*/}}
{{- define "openanomaly.fullname" -}}
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
{{- define "openanomaly.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Common labels
*/}}
{{- define "openanomaly.labels" -}}
helm.sh/chart: {{ include "openanomaly.chart" . }}
{{ include "openanomaly.selectorLabels" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{/*
Selector labels
*/}}
{{- define "openanomaly.selectorLabels" -}}
app.kubernetes.io/name: {{ include "openanomaly.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{/*
Create the name of the service account to use
*/}}
{{- define "openanomaly.serviceAccountName" -}}
{{- if .Values.serviceAccount.create }}
{{- default (include "openanomaly.fullname" .) .Values.serviceAccount.name }}
{{- else }}
{{- default "default" .Values.serviceAccount.name }}
{{- end }}
{{- end }}

{{/*
Get image tag
*/}}
{{- define "openanomaly.imageTag" -}}
{{- .Values.image.tag | default .Chart.AppVersion }}
{{- end }}

{{/*
Get full image name for a component
*/}}
{{- define "openanomaly.image" -}}
{{- $mode := . -}}
{{- $root := index . 1 -}}
{{- $registry := $root.Values.image.registry -}}
{{- $repository := $root.Values.image.repository -}}
{{- $tag := include "openanomaly.imageTag" $root -}}
{{- printf "%s/%s:%s-%s" $registry $repository $tag $mode -}}
{{- end }}
