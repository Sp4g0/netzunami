# Netzunami — Network Config Analyzer AI

**Prototipo v0.1.0 — bozza da testare**

## Concept

Terminale SSH intelligente (tipo PuTTY/SecureCRT) che analizza configurazioni di rete in tempo reale.

**Per chi è:**
- **Junior**: impara dalle best practice, capisce cosa controllare, evita errori comuni
- **Senior**: velocizza i check di routine, bulk su N apparati, non perde dettagli

## Installazione

```bash
pip install -e .            # base (leggero, sklearn)
pip install -e ".[ai]"      # + AI embedding (sentence-transformers, FAISS, PyMuPDF)
python -m netzunami.gui     # Avvia GUI
```

**Base** (scikit-learn Tfidf): ~50MB, embedding testuali, nessuna GPU
**AI** (+torch): ~2GB, embedding semantici, indicizzazione PDF

## GUI (Tkinter)

- Terminale colorato stile PuTTY/SecureCRT
- Pannello sessioni a sinistra (salvate in ~/.netzunami/sessions.json)
- Pannello NetSense AI a destra (findings in tempo reale)
- Vault password crittografato (Fernet)
- Import sessioni da SecureCRT (.ini)
- Comando bulk su N apparati
- Shortcut: Ctrl+N nuova, Ctrl+Q quick connect, Ctrl+T tab, Ctrl+W chiudi

## Per Junior e Senior

- **Junior**: impara dalle best practice embedded, capisce cosa controllare, non sbaglia configurazioni di base
- **Senior**: velocizza audit, bulk change, non perde dettagli su decine di apparati
- **Futuro**: change massivi con revisione AI (diff strutturato, rollback pianificato)

## Prossimo

1. SSH hop multiplo (catena bastion)
2. Parser multi-vendor (Huawei VRP, Juniper JunOS)
3. Dataset sessioni → training incrementale feedback loop
4. Change massivi con revisione AI (diff strutturato, rollback)
5. TUI curses per split terminale (SSH + chat laterale)
