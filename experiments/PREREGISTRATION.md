# Preregistration Manifest

- Git commit: c4d735de9a73da3ddcd44d6dc51f2e4aa553caca
- Created UTC: 2026-11-09T04:14:20.270200+00:00
- Manifest digest: 1448d90e4a3212ff90195d2018cc4349b5104e5f40d230ec762c517900f783be

## Group: design

| path | SHA-256 | bytes |
| --- | --- | --- |
| docs/EXPERIMENT_DESIGN.md | 986450fea37dcd8fff606d2bcb6693f3d8931634f644aca52cb591be0e71d496 | 19534 |

## Group: playbooks

| path | SHA-256 | bytes |
| --- | --- | --- |
| experiments/payloads/README.md | 35adb45fda699b053e3cb61a1088f0f50a4edbd4448cf55c8e0210eb7175a4af | 701 |
| experiments/payloads/playbook_0.txt | f94adea24cc12c3ae473272130e50b6dd2a810190eb5b2bd8e9b70a57effc3fc | 806 |
| experiments/payloads/playbook_1.txt | 99d36e2ae761b4adccfff497a76e839152abbc32e611bc7ce75bf7aa4a227f83 | 733 |
| experiments/payloads/playbook_2.txt | 88b6b0bdf3bbd7206d1e8a452be211272ac0fc551e567d11950cb9cb4ee8ce2a | 687 |

## Group: configs

| path | SHA-256 | bytes |
| --- | --- | --- |
| experiments/configs/free_flow.yaml | f5ae3c6a11185df7381523f180c07505bce32c7364d087a3c4699c690db7809c | 1015 |
| experiments/configs/matrices/control_complete.yaml | cc065d93e251b3240f075faa0e50ea59f84b3653661f48f76692bbcfe794eaa2 | 146 |
| experiments/configs/matrices/control_ring.yaml | a1fa4a56ad422372cf7a14f31abfb2f62e10e9482d1e3e8caf848da84208b9e9 | 148 |
| experiments/configs/matrices/free_flow.yaml | 8f954a785408085e8e3dbe49b12707219a0ed84335bdc322c2caff29552d690d | 142 |
| experiments/configs/matrices/gate_cost.yaml | 72bc19d751869c5e7bfd402d6a07be9cad1acb5db8b53040a3bf57d4aaef2ec8 | 139 |
| experiments/configs/matrices/gating.yaml | 36a99aec2f4336a3fa295e2e7d9f67e43828a7fc7c8f05aeacc336330c240ff9 | 137 |
| experiments/configs/matrices/pilot.yaml | 9718c741b4920eca11b3bc24e24607930085bb332f384d6316523dea0cec4537 | 127 |
| experiments/configs/matrices/train_clean_complete.yaml | c531883ab7177865599d6eb33d7772e618c471e613ea7eb50b1dc2ee967fbf3d | 115 |
| experiments/configs/matrices/train_clean_ring.yaml | 8824de6d0ccf515c670b83814850fb58d1bbad2a73c7244c16eaee406da05486 | 115 |
| experiments/configs/matrices/train_infected_complete.yaml | 5daef78aa1ebdbd9e9947b887675c15c1d72e424ad18575bd82a612e18fe8f3b | 129 |
| experiments/configs/matrices/train_infected_ring.yaml | dc71eb15aac6e0c40e7ab10ba8816772456b537270053e207d5b286d3df55692 | 125 |
| experiments/configs/pilot.yaml | ca6362fbe4dc8097618e55df563179396878f21cdf13b2d1cc6b148e843efbf5 | 1015 |

## Group: analysis_code

| path | SHA-256 | bytes |
| --- | --- | --- |
| src/swarmlab/detectors/graph.py | 3be6b2cd38205365db01ef2f085c1a97a46b2233cc96664f2f380e52d1ef7257 | 1177 |
| src/swarmlab/detectors/graph_detector.py | 8978a8e9d521bbe5fd8a44af8b184328d0d3e8e427bb615336f56df009823dd8 | 854 |
| src/swarmlab/detectors/guardrail.py | 9572659522df88aa0750f5e9bee9a787af15afd688ecb89564cde9035f886f4a | 8170 |
| src/swarmlab/detectors/immunity.py | b01a6b52b803706b3fb0a2b204b69abbc9de91f3b2397a4e99cf18d365a6847d | 6283 |
| src/swarmlab/detectors/layered.py | c90f857839b0d9ff384c46be4c81a0c66d839ab5ff665a2104c262037c3b0b52 | 4473 |
| src/swarmlab/detectors/lexical.py | b34c0159be51ee069d19a7b734f8920d671c43cd79f4c9d043ac93b1b1cd6b70 | 7503 |
| src/swarmlab/detectors/thresholds.py | faf9c0ca41e80f542ad5f780421f086fce162bad03b99908c52bcc14c5dab4b6 | 3402 |
| src/swarmlab/detectors/verifiers.py | 5f3491ae7d9acb31e7e1454eab2306813146524409ee98614cbb11cdd038692c | 5897 |
| src/swarmlab/metrics/analysis.py | 1a3bd505c86a3f37dca206136840a1af9c3a14222629425e9aa986e0a67820b3 | 41844 |
| src/swarmlab/metrics/events.py | e45cfb99a61d011474943439313d261b3e8b9781705aeebd355ac58c1b5588cd | 2407 |
| src/swarmlab/metrics/extract.py | 299e1b1627f696e09da57131783ad3e1fb181626b1a709479c3c064e414b39a0 | 17417 |
| src/swarmlab/metrics/plots.py | 037eb93f325665e81be80b0681f41db757f960c471008935746a5f051223ee80 | 7623 |
| src/swarmlab/metrics/stats.py | 28531798e3b8f3b22a5e5122b666d83219dcb4dc3724b8b04f386af5855f7f8c | 7220 |
| src/swarmlab/scoring.py | 3940b08d2e1ddc4a7e72053e5264686cbcb815c1e3a86721ec95db04028ebc1a | 5343 |
| src/swarmlab/training.py | cf19ced77432163b2b820f46ec77fd9b2a0d995d53e1d6cdc4eed9683dbc3481 | 31245 |

## Group: runtime_code

| path | SHA-256 | bytes |
| --- | --- | --- |
| src/swarmlab/__init__.py | 45cdf2af3c4b7b1221e61a523d80fd7b82c8833e27155f160f47604804a5959c | 83 |
| src/swarmlab/__main__.py | 5eb01c68f048551473faf411df2bd07655344329a4fa2036098bd8a250ca8de9 | 123 |
| src/swarmlab/batch.py | 17a18fdc8530d07af6b2f6cd66fc61d7eb3c9605b0515285028e6f6c0b222f30 | 7769 |
| src/swarmlab/cli.py | 30899cec3c13424ac98f1f5e676eda363ca2c30621d6ddf9e309e489ea41d098 | 1269 |
| src/swarmlab/commands/analyze.py | 1aea85f589878829ae47fdd9719407ae5aa87cb3f0bb10ccc5c4df3198442acf | 727 |
| src/swarmlab/commands/batch.py | 3a6f6d30ef6de7fb41e65132192b960d45fb8d734112421162d047791c4350fa | 3852 |
| src/swarmlab/commands/prereg.py | af6bcc2f2b46027308e1253f5447eea131909f57305c48774917c6d7da0eb7eb | 1101 |
| src/swarmlab/commands/run_episode.py | f4cbb269d1566d3b1bf0068b4a2d6b11261265ecbe5cbcc907dc5bb2cf724262 | 2607 |
| src/swarmlab/commands/score.py | 27bd63d98e80ab61ef9838e0b2406fd6291b53e2aa253a9b28702564660e3145 | 813 |
| src/swarmlab/commands/train_detectors.py | 875e655cca5c7215941f0c96f51faf8101cb3167ce5cd99db0b61989f42daf4f | 2600 |
| src/swarmlab/config.py | 04f4bb7034c7809b213b0c20fb7a9c52eeb98b69844a4625abebb4030ac92038 | 996 |
| src/swarmlab/detectors/graph.py | 3be6b2cd38205365db01ef2f085c1a97a46b2233cc96664f2f380e52d1ef7257 | 1177 |
| src/swarmlab/detectors/graph_detector.py | 8978a8e9d521bbe5fd8a44af8b184328d0d3e8e427bb615336f56df009823dd8 | 854 |
| src/swarmlab/detectors/guardrail.py | 9572659522df88aa0750f5e9bee9a787af15afd688ecb89564cde9035f886f4a | 8170 |
| src/swarmlab/detectors/immunity.py | b01a6b52b803706b3fb0a2b204b69abbc9de91f3b2397a4e99cf18d365a6847d | 6283 |
| src/swarmlab/detectors/layered.py | c90f857839b0d9ff384c46be4c81a0c66d839ab5ff665a2104c262037c3b0b52 | 4473 |
| src/swarmlab/detectors/lexical.py | b34c0159be51ee069d19a7b734f8920d671c43cd79f4c9d043ac93b1b1cd6b70 | 7503 |
| src/swarmlab/detectors/thresholds.py | faf9c0ca41e80f542ad5f780421f086fce162bad03b99908c52bcc14c5dab4b6 | 3402 |
| src/swarmlab/detectors/verifiers.py | 5f3491ae7d9acb31e7e1454eab2306813146524409ee98614cbb11cdd038692c | 5897 |
| src/swarmlab/execution.py | c69730912d4d9c4bfa87d5698b88e515f5023c1624eb6a3a932e4a50b33c1fc9 | 20798 |
| src/swarmlab/llm/budget.py | 64ec2077bf470b0fd86b4c64b0622df3d5187f0e1a08033de4fc3bf812a6a341 | 4910 |
| src/swarmlab/llm/guarded.py | b39fc7e5e96a53987db3ec58a8187f5169264aeadd40e1c6b757f0562549ac9c | 6135 |
| src/swarmlab/llm/ledger.py | 47b404a0fe1afa9923a27ee03d1263807a13fb4385bce21ae984125a672d24f5 | 6103 |
| src/swarmlab/llm/limiter.py | 4c98377e604be0d8415ccef3db3b43cdc428d1bfe13031eb8180727ebb7f46aa | 3423 |
| src/swarmlab/llm/mock.py | 8ae4731434cc575a5c02a200e77f331a6a16bf7d55abffb8d05b1809ffc8ebc1 | 3371 |
| src/swarmlab/llm/providers/_common.py | 62bda01453e437a54f78bb2ea20bcb1251ce49f5b21ad75fbb6f39b4f24bdf81 | 2892 |
| src/swarmlab/llm/providers/adaption.py | 9c691e8101cfe663122463c73c3dd486ad19e512eddf1bc6d12bab176e684752 | 3279 |
| src/swarmlab/llm/providers/muse.py | 6d52eda8f24ebe9355af700050f71c8d46b6ddb3f67958e6828e33abc4c4d5c2 | 3121 |
| src/swarmlab/llm/providers/vertex.py | 6d366d661990518b203cc7483ec9fb0a8a4becbdbd230e0214f2a7b3e9002110 | 4575 |
| src/swarmlab/llm/secrets.py | ec62ff5eea3e3bc7b9bac8f7250b2ee0974c3d60b9e98760a966fd9b86835dc6 | 859 |
| src/swarmlab/metrics/analysis.py | 1a3bd505c86a3f37dca206136840a1af9c3a14222629425e9aa986e0a67820b3 | 41844 |
| src/swarmlab/metrics/events.py | e45cfb99a61d011474943439313d261b3e8b9781705aeebd355ac58c1b5588cd | 2407 |
| src/swarmlab/metrics/extract.py | 299e1b1627f696e09da57131783ad3e1fb181626b1a709479c3c064e414b39a0 | 17417 |
| src/swarmlab/metrics/plots.py | 037eb93f325665e81be80b0681f41db757f960c471008935746a5f051223ee80 | 7623 |
| src/swarmlab/metrics/stats.py | 28531798e3b8f3b22a5e5122b666d83219dcb4dc3724b8b04f386af5855f7f8c | 7220 |
| src/swarmlab/prereg.py | 5781c772b066b50d13eff130c579782ebdb0c38a166c8571ec3c43c029e7a65c | 7185 |
| src/swarmlab/schema.py | 2223defcc093a50636c930dbe83d793de9a5e9b1c2c38fef435b5ed7bbb620d2 | 5875 |
| src/swarmlab/scoring.py | 3940b08d2e1ddc4a7e72053e5264686cbcb815c1e3a86721ec95db04028ebc1a | 5343 |
| src/swarmlab/swarm/agent.py | 0255390ae845e0c24ada9b0532d643c7afd3cebd6c3f20ffcf03c73d9ffbef5f | 1487 |
| src/swarmlab/swarm/board.py | c843fefe6b1f4a4336f948b164f5e698073bcca72e957fb780e2fd638f305a25 | 1962 |
| src/swarmlab/swarm/prompts.py | 46354e28243b91f0e661f6320f6a0ec417aa9cdc179ea6824f1be516be1b2658 | 7450 |
| src/swarmlab/swarm/runner.py | 1fac0346b4098728ac22bc845bf0207b8834bf844e91cfa914e50529c38e8ba4 | 10313 |
| src/swarmlab/swarm/tools.py | 4c71e7184789d86b026d8ce1c93c952672361c3daa9bfa447799521e8a0dff5b | 719 |
| src/swarmlab/swarm/topology.py | 78c5ba7927a8ba3ec271b80696fdbb6613890d78aab7ad260fe0dd49ec8f0b07 | 458 |
| src/swarmlab/training.py | cf19ced77432163b2b820f46ec77fd9b2a0d995d53e1d6cdc4eed9683dbc3481 | 31245 |
| src/swarmlab/world/generator.py | a417bf00d9408c119e8f4eb02ed74a2231ef710befb62fabee8541c3ff62cdf7 | 6678 |
| src/swarmlab/world/types.py | 68161e1268993f57ee1b6c20bcdeba524240721a2609df4e2b81b4a0a7c78e11 | 996 |

## Group: prompts

| path | SHA-256 | bytes |
| --- | --- | --- |
| src/swarmlab/swarm/prompts.py | 46354e28243b91f0e661f6320f6a0ec417aa9cdc179ea6824f1be516be1b2658 | 7450 |

This manifest is created before any TEST episode runs. The tag prereg-v1 is created by the human.
