@echo off
REM ==========================================================
REM DIANA 0.4 - OLLAMA AUXILIAR EM OUTRA PORTA (CPU)
REM ==========================================================
REM Feche esta janela para desligar a instancia auxiliar.
REM O modelo so sera carregado quando Planner/Resumidor chamarem a API.

set OLLAMA_HOST=127.0.0.1:11435
set CUDA_VISIBLE_DEVICES=-1
set OLLAMA_NUM_PARALLEL=1

ollama serve
pause
