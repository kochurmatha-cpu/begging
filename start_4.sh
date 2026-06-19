#!/data/data/com.termux/files/usr/bin/bash
cd "$(dirname "$0")" || { echo "Cannot find script location"; exit 1; }

tmux new-session -d -s mibox
tmux split-window -h
tmux split-window -v
tmux select-pane -t 0
tmux split-window -v

tmux send-keys -t 0 "python script.py" C-m
tmux send-keys -t 1 "python script.py" C-m
tmux send-keys -t 2 "python script.py" C-m
tmux send-keys -t 3 "python script.py" C-m

tmux attach-session -t mibox
