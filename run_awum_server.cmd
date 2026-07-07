@echo off
cd /d "%~dp0"
python run_awum_server.py > awum-server.out.log 2> awum-server.err.log
