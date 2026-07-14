from bot.captions import DEFAULT_LINKS_BLOCK, TELEGRAM_CAPTION_LIMIT, build_caption

def test_html_escaping_and_links_not_escaped():
    text=build_caption('<b>x</b> & y')
    assert '&lt;b&gt;x&lt;/b&gt; &amp; y' in text
    assert DEFAULT_LINKS_BLOCK in text
    assert '&lt;a href' not in text

def test_caption_limit_keeps_links():
    text=build_caption('x'*5000)
    assert len(text) <= TELEGRAM_CAPTION_LIMIT
    assert text.endswith(DEFAULT_LINKS_BLOCK)

def test_empty_caption_only_links():
    assert build_caption(None) == DEFAULT_LINKS_BLOCK


def test_custom_links_block_not_escaped():
    custom = '<a href="https://example.com">Example</a>'
    text = build_caption('<b>x</b>', custom)
    assert '&lt;b&gt;x&lt;/b&gt;' in text
    assert custom in text
    assert '&lt;a href' not in text
