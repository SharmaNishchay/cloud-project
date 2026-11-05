import subprocess, sys


def test_nacl_sample_packets_pass():
    r = subprocess.run([sys.executable, "tools/nacl_sim.py", "network/nacl.json",
                        "network/packets_sample.jsonl", "--check"], capture_output=True, text=True)
    assert "6 / 6" in r.stdout
