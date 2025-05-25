#!/bin/bash
sudo systemctl daemon-reexec 
sudo systemctl daemon-reload
sudo systemctl restart tun_rf24.service