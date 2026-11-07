# Copy this file to start-hindsight.ps1 and put your Groq key on line 3 (start-hindsight.ps1 is git-ignored).
# Run with:  powershell -ExecutionPolicy Bypass -File .\start-hindsight.ps1
$env:HINDSIGHT_API_LLM_PROVIDER="none"          # "groq" enables LLM fact extraction + reflect; "none" = semantic memory store
$env:HINDSIGHT_API_LLM_API_KEY="gsk_your_groq_key"
$env:HINDSIGHT_API_LLM_MODEL="openai/gpt-oss-120b"
hindsight-api                                      # if not found, use the full path to hindsight-api.exe in your Python Scripts folder
