# Netzunami — Network Config Analyzer AI

**Prototipo v0.1.0 — bozza da testare**

## Concept

CLI Python che si connette via SSH a apparati di rete, legge la running-config e la analizza con:
- **Regole deterministiche**: pattern matching su misconfigurazioni note (Cisco IOS)
- **Embedding AI**: manuali tecnici (PDF) indicizzati → ricerca semantica su configurazioni reali
- **Chat laterale**: listener che osserva una sessione live e suggerisce findings in tempo reale
- **Bastion/Jump host**: ProxyJump nativo per ambienti con hop

## Installazione

```bash
pip install -e .
```

Dipende da: `sentence-transformers`, `faiss-cpu`, `paramiko`, `PyMuPDF`, `click`, `rich`.

## Comandi

| Comando | Cosa fa |
|---------|---------|
| `netzunami ssh <host>` | Connessione SSH + dump config + analisi |
| `netzunami analyze <file>` | Analisi file config offline |
| `netzunami index <dir>` | Indicizza manuali PDF/TXT in knowledge base |
| `netzunami search "query"` | Cerca nella knowledge base |
| `netzunami listen <log>` | Ascolta sessione live in tempo reale |
| `netzunami info` | Stato: modello, vettori, config |

## Architettura

```
netzunami/
├── netzunami/
│   ├── cli.py            # CLI (click)
│   ├── config.py         # Config da ~/.netzunami/config.yaml
│   ├── connector.py      # SSH + bastion/jump host (paramiko)
│   ├── parser.py         # Running-config parser (Cisco IOS)
│   ├── embedder.py       # sentence-transformers wrapper
│   ├── indexer.py        # PDF ingestion + FAISS indexing
│   ├── analyzer.py       # Rule-based + knowledge-based analysis
│   ├── listener.py       # Real-time session listener
│   └── models.py         # Finding, ConfigBlock, Severity, etc.
├── pyproject.toml
└── IDEA.md
```

## Regole incluse (Cisco IOS)

CRITICAL: default route senza tracking, enable secret assente, SSHv1
HIGH: HTTP server attivo
MEDIUM: MTU mismatch, STP guard, BGP peer, NTP source, AAA, SNMP community, username priv15
LOW: port-channel, VLAN, OSPF, ACL, password encryption
INFO: no shutdown, no ip domain-lookup, SSHv2, HTTPS, enable secret

## Prossimo

1. SSH hop multiplo (catena bastion)
2. Parser multi-vendor (Huawei VRP, Juniper JunOS)
3. Dataset sessioni → training incrementale feedback loop
4. TUI curses per split terminale (SSH + chat laterale)
