param(
    [Parameter(Mandatory = $true)] [string] $ProjectId,
    [string] $Region = "us-central1",
    [string] $Repository = "jobpull",
    [string] $ImageName = "jobpull",
    [string] $ServiceName = "jobpull-ui",
    [string] $JobName = "jobpull-pipeline",
    [string] $ScheduleName = "jobpull-daily",
    [string] $Schedule = "0 6 * * *",
    [string] $SchedulerServiceAccount = "jobpull-scheduler",
    [switch] $EnableGemini,
    [switch] $AllowUnauthenticated
)

$ErrorActionPreference = "Stop"
$image = "$Region-docker.pkg.dev/$ProjectId/$Repository/${ImageName}:latest"
$secretMap = "MONGODB_URI=mongodb-uri:latest,FIRECRAWL_API_KEY=firecrawl-api-key:latest"
if ($EnableGemini) {
    $secretMap += ",GEMINI_API_KEY=gemini-api-key:latest"
}

Write-Host "Using project $ProjectId in $Region"
gcloud config set project $ProjectId | Out-Host
gcloud services enable run.googleapis.com artifactregistry.googleapis.com cloudbuild.googleapis.com cloudscheduler.googleapis.com | Out-Host

gcloud artifacts repositories describe $Repository --location $Region --project $ProjectId *> $null
if ($LASTEXITCODE -ne 0) {
    gcloud artifacts repositories create $Repository `
        --repository-format=docker --location=$Region --description="JobPull images" | Out-Host
}

Write-Host "Building $image"
# Build context is BE/ (backend lives there in the monorepo; Dockerfile + requirements are inside it).
gcloud builds submit --tag $image BE | Out-Host

$authFlag = if ($AllowUnauthenticated) { "--allow-unauthenticated" } else { "--no-allow-unauthenticated" }

Write-Host "Deploying dashboard service $ServiceName"
gcloud run deploy $ServiceName `
    --image=$image `
    --region=$Region `
    --port=8080 `
    --cpu=1 `
    --memory=512Mi `
    --min=0 `
    --max=1 `
    --set-env-vars="DB_NAME=job-pull-simple,JOBS_COLLECTION=jobs" `
    --set-secrets=$secretMap `
    $authFlag | Out-Host

Write-Host "Deploying scraper/analyzer job $JobName"
gcloud run jobs deploy $JobName `
    --image=$image `
    --region=$Region `
    --command=python `
    --args=pipeline.py `
    --tasks=1 `
    --max-retries=0 `
    --task-timeout=1h `
    --cpu=1 `
    --memory=1Gi `
    --set-env-vars="DB_NAME=job-pull-simple,JOBS_COLLECTION=jobs" `
    --set-secrets=$secretMap | Out-Host

Write-Host "Granting Cloud Scheduler permission to invoke $JobName"
$schedulerEmail = "$SchedulerServiceAccount@$ProjectId.iam.gserviceaccount.com"
gcloud iam service-accounts describe $schedulerEmail --project=$ProjectId *> $null
if ($LASTEXITCODE -ne 0) {
    gcloud iam service-accounts create $SchedulerServiceAccount `
        --project=$ProjectId `
        --display-name="JobPull Cloud Scheduler" | Out-Host
}

gcloud run jobs add-iam-policy-binding $JobName `
    --region=$Region `
    --project=$ProjectId `
    --member="serviceAccount:$schedulerEmail" `
    --role=roles/run.invoker | Out-Host

$schedulerUri = "https://run.googleapis.com/v2/projects/$ProjectId/locations/$Region/jobs/${JobName}:run"
Write-Host "Configuring daily Cloud Scheduler trigger $ScheduleName ($Schedule, Asia/Kolkata)"
gcloud scheduler jobs describe $ScheduleName --location=$Region --project=$ProjectId *> $null
if ($LASTEXITCODE -eq 0) {
    gcloud scheduler jobs update http $ScheduleName `
        --location=$Region `
        --project=$ProjectId `
        --schedule="$Schedule" `
        --time-zone="Asia/Kolkata" `
        --uri=$schedulerUri `
        --http-method=POST `
        --oauth-service-account-email=$schedulerEmail | Out-Host
} else {
    gcloud scheduler jobs create http $ScheduleName `
        --location=$Region `
        --project=$ProjectId `
        --schedule="$Schedule" `
        --time-zone="Asia/Kolkata" `
        --uri=$schedulerUri `
        --http-method=POST `
        --oauth-service-account-email=$schedulerEmail | Out-Host
}

Write-Host "Deployment complete. Test the batch with:"
Write-Host "  gcloud run jobs execute $JobName --region=$Region --wait"
Write-Host "Check the schedule with:"
Write-Host "  gcloud scheduler jobs describe $ScheduleName --location=$Region"
