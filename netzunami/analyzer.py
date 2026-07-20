import os
import re
import numpy as np
from pathlib import Path
from .models import Finding, Severity, AnalysisResult, ConfigBlock
from .parser import parse_running_config
from .embedder import embed
from .indexer import index_manuals, search


COMMON_ISSUES = {
    "cisco": [
        {
            "pattern": r"ip mtu (\d+)",
            "severity": Severity.MEDIUM,
            "title": "Configurazione MTU",
            "detail": "MTU configurato a livello di interfaccia. Verificare coerenza su entrambi i lati del link.",
            "suggestion": "Verificare MTU match su link adjacency. Usare 'show interface' per conferma.",
        },
        {
            "pattern": r"channel-group (\d+) mode (active|passive|on)",
            "severity": Severity.LOW,
            "title": "Port-channel configurato",
            "detail": "Port-channel attivo. Verificare consistenza membri su entrambi i lati.",
            "suggestion": "Verificare 'show etherchannel summary' per tutti i membri attivi.",
        },
        {
            "pattern": r"no shutdown",
            "severity": Severity.INFO,
            "title": "Interfaccia abilitata",
            "detail": "Interfaccia in stato 'no shutdown'. OK.",
            "suggestion": "",
        },
        {
            "pattern": r"shutdown",
            "severity": Severity.INFO,
            "title": "Interfaccia disabilitata",
            "detail": "Interfaccia in stato 'shutdown'. Verifica se intenzionale.",
            "suggestion": "Usare 'no shutdown' per abilitare.",
        },
        {
            "pattern": r"spanning-tree (bpduguard|portfast)",
            "severity": Severity.MEDIUM,
            "title": "STP Edge/BPDUGuard configurato",
            "detail": "Protezione STP su porta access/edge.",
            "suggestion": "Verificare che la porta sia realmente un edge port.",
        },
        {
            "pattern": r"vlan (\d+)",
            "severity": Severity.LOW,
            "title": "VLAN configurata",
            "detail": "VLAN presente in configurazione.",
            "suggestion": "",
        },
        {
            "pattern": r"ip route 0\.0\.0\.0 0\.0\.0\.0",
            "severity": Severity.INFO,
            "title": "Default route presente",
            "detail": "Rotta di default configurata globalmente.",
            "suggestion": "Verificare next-hop raggiungibile.",
        },
        {
            "pattern": r"ip route 0\.0\.0\.0 0\.0\.0\.0 (\S+)",
            "severity": Severity.CRITICAL,
            "title": "Default route senza tracking",
            "detail": "Rotta di default senza IP SLA/object tracking. Se il next-hop cade, il traffico viene blackholed.",
            "suggestion": "Aggiungere 'track' object e 'ip route 0.0.0.0 0.0.0.0 <next-hop> track <n>'",
        },
        {
            "pattern": r"router ospf (\d+)",
            "severity": Severity.LOW,
            "title": "OSPF configurato",
            "detail": "Processo OSPF attivo.",
            "suggestion": "",
        },
        {
            "pattern": r"neighbor (\S+) remote-as",
            "severity": Severity.MEDIUM,
            "title": "BGP neighbor configurato",
            "detail": "Peer BGP definito.",
            "suggestion": "Verificare reachability e stato sessione BGP.",
        },
        {
            "pattern": r"ip access-list extended",
            "severity": Severity.LOW,
            "title": "ACL extended presente",
            "detail": "Access-list extended configurata.",
            "suggestion": "",
        },
        {
            "pattern": r"no ip domain-lookup",
            "severity": Severity.INFO,
            "title": "Domain lookup disabilitato",
            "detail": "DNS lookup disabilitato. Buona pratica.",
            "suggestion": "",
        },
        {
            "pattern": r"ip domain-name\s+\S+",
            "severity": Severity.INFO,
            "title": "Domain name configurato",
            "detail": "Domain name presente. Usato per generazione certificati e chiavi.",
            "suggestion": "",
        },
        {
            "pattern": r"crypto pki",
            "severity": Severity.MEDIUM,
            "title": "PKI/Certificati configurati",
            "detail": "Infrastruttura a chiave pubblica presente.",
            "suggestion": "Verificare scadenza certificati e trustpoint.",
        },
        {
            "pattern": r"ntp server",
            "severity": Severity.LOW,
            "title": "NTP configurato",
            "detail": "Server NTP configurato.",
            "suggestion": "Verificare sincronizzazione con 'show ntp status'.",
        },
        {
            "pattern": r"ntp server (\S+)",
            "severity": Severity.LOW,
            "title": "NTP source tracking",
            "detail": "Verificare che il source IP per NTP sia configurato con 'ntp source <interface>'",
            "suggestion": "Se non configurato, aggiungere 'ntp source Loopback0'",
        },
        {
            "pattern": r"username (\S+) privilege 15",
            "severity": Severity.MEDIUM,
            "title": "Utente privilege 15",
            "detail": "Utente con privilegi massimi. Valutare se necessario.",
            "suggestion": "Usare privilege level appropriato o AAA con autorizzazione per-command.",
        },
        {
            "pattern": r"aaa new-model",
            "severity": Severity.LOW,
            "title": "AAA model attivo",
            "detail": "AAA new-model configurato.",
            "suggestion": "",
        },
        {
            "pattern": r"service password-encryption",
            "severity": Severity.LOW,
            "title": "Password encryption attiva",
            "detail": "Password encryption (type 7) attiva.",
            "suggestion": "Considerare type 8/9 (SHA256/SCRYPT) per password più sicure.",
        },
        {
            "pattern": r"enable secret",
            "severity": Severity.INFO,
            "title": "Enable secret configurato",
            "detail": "Enable password protetta da hash. Buona pratica.",
            "suggestion": "",
        },
        {
            "pattern": r"no enable secret",
            "severity": Severity.CRITICAL,
            "title": "Enable secret NON configurato",
            "detail": "Manca protezione su accesso privilegiato.",
            "suggestion": "Configurare 'enable secret <password>'",
        },
        {
            "pattern": r"snmp-server community (\S+) (RO|RW)",
            "severity": Severity.MEDIUM,
            "title": "SNMP community",
            "detail": "Community SNMP configurata. Risk se non ristretta da ACL.",
            "suggestion": "Aggiungere ACL: 'snmp-server community XXXX RO <acl>'",
        },
        {
            "pattern": r"ip http server",
            "severity": Severity.HIGH,
            "title": "HTTP server attivo",
            "detail": "HTTP server abilitato. Vettore di attacco se non necessario.",
            "suggestion": "Disabilitare con 'no ip http server' o usare solo HTTPS con ACL.",
        },
        {
            "pattern": r"ip http secure-server",
            "severity": Severity.LOW,
            "title": "HTTPS server attivo",
            "detail": "HTTPS server abilitato. Preferibile a HTTP.",
            "suggestion": "",
        },
        {
            "pattern": r"ip ssh version 2",
            "severity": Severity.INFO,
            "title": "SSHv2 configurato",
            "detail": "SSH versione 2. OK.",
            "suggestion": "",
        },
        {
            "pattern": r"ip ssh version 1",
            "severity": Severity.HIGH,
            "title": "SSHv1 attivo",
            "detail": "SSH versione 1 è insicura e deprecata.",
            "suggestion": "Configurare 'ip ssh version 2'",
        },
    ]
}


def analyze_with_rules(blocks: list[ConfigBlock], vendor: str = "cisco") -> list[Finding]:
    findings: list[Finding] = []
    rules = COMMON_ISSUES.get(vendor, [])

    for block in blocks:
        full_text = "\n".join(line.text for line in block.lines)

        for rule in rules:
            matches = re.findall(rule["pattern"], full_text, re.IGNORECASE)
            if matches:
                matched_lines = [
                    line.number
                    for line in block.lines
                    if re.search(rule["pattern"], line.text, re.IGNORECASE)
                ]
                findings.append(
                    Finding(
                        severity=rule["severity"],
                        title=rule["title"],
                        detail=rule["detail"],
                        config_lines=matched_lines,
                        suggestion=rule["suggestion"],
                    )
                )

    return findings


def analyze_with_knowledge(
    blocks: list[ConfigBlock], index, metadata: list[dict], model_name: str = "all-MiniLM-L6-v2", top_k: int = 3
) -> list[Finding]:
    findings: list[Finding] = []
    seen = set()

    for block in blocks:
        block_text = "\n".join(line.text for line in block.lines)
        results = search(index, metadata, block_text, model_name, top_k)

        for meta, score in results:
            if score < 0.6:
                continue
            key = (meta["source"], meta["chunk"])
            if key in seen:
                continue
            seen.add(key)

            findings.append(
                Finding(
                    severity=Severity.INFO,
                    title=f"Manuale: {meta['source']} (sez.{meta['chunk']})",
                    detail=f"Similarità: {score:.2f} — {meta['text'][:150]}",
                    similarity=score,
                )
            )

    return findings
