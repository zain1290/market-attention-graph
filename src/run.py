import subprocess, sys, pathlib, signal, time, os

PROJECT_ROOT = pathlib.Path(__file__).resolve().parent
PYTHON = sys.executable
BACKOFF = 3
SCRIPTS = [
    "collectors/stream_binance.py",
    "collectors/stream_alpaca.py",
    "collectors/stream_gdelt.py",
    "collectors/stream_rss.py",
    "collectors/stream_twitter.py",
    "data/writer.py"
]
processes = {}

def launch(s):
    path = PROJECT_ROOT / s
    print(f"Starting {path}")
    return subprocess.Popen([PYTHON, str(path)])

def shutdown(*_):
    print("\nStopping all processes …")
    for p in processes:
        p.terminate()
    time.sleep(3)

    for p in processes:
        if p.poll() is None:
            p.kill()

def main():
    try:
        for script in SCRIPTS:
            processes[launch(script)] = script

        signal.signal(signal.SIGINT, shutdown)
        signal.signal(signal.SIGTERM, shutdown)

        while True:
            time.sleep(1)
            for p, script in list(processes.items()):
                if p.poll() is None:  # still running
                    continue

                rc = p.returncode
                print(f" {script} exited with {rc}; restarting in {BACKOFF}s …")
                del processes[p]
                time.sleep(BACKOFF)
                processes[launch(script)] = script

    except KeyboardInterrupt:
        shutdown()

if __name__ == "__main__":
    main()