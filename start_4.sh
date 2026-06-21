#!/data/data/com.termux/files/usr/bin/bash

cd "$(dirname "$0")" || { echo "Cannot find begging folder"; exit 1; }

python script.py --setup

if [ $? -ne 0 ]; then
    echo "Setup failed. Fix tokens and try again."
    exit 1
fi

echo "Launching 4 Paths of Begging..."
tmux new-session -d -s begging

tmux split-window -h
tmux split-window -v
tmux select-pane -t 0
tmux split-window -v

tmux send-keys -t 0 "python script.py --slot 1" C-m
tmux send-keys -t 1 "python script.py --slot 2" C-m
tmux send-keys -t 2 "python script.py --slot 3" C-m
tmux send-keys -t 3 "python script.py --slot 4" C-m

tmux attach-session -t begging
