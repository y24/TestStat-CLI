param(
    [string]$Message
)

Set-Location $PSScriptRoot

if ($Message) {
    alembic revision --autogenerate -m $Message
} else {
    alembic upgrade head
}
