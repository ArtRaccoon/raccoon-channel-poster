from pathlib import Path

def test_systemd_path():
    text=Path('systemd/raccoon-channel-poster.service').read_text()
    assert 'WorkingDirectory=/home/postingbot/bots/raccoon-channel-poster' in text
    assert 'Requires=raccoon-sing-box.service' in text
