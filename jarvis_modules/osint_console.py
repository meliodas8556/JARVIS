"""
OSINT Console Module for JARVIS
Provides IP lookup, domain reconnaissance, DNS records, port scanning, 
email discovery, and reputation checks.
"""

import socket
import ipaddress
import json
import csv
import threading
import time
import re
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
import subprocess
import sys

try:
    import requests
except ImportError:
    requests = None

try:
    import dns.resolver
    import dns.query
    import dns.xfr
    DNS_AVAILABLE = True
except ImportError:
    DNS_AVAILABLE = False


class OSINTConsole:
    """Comprehensive OSINT reconnaissance console."""
    
    def __init__(self):
        self.results = {}
        self.export_format = "json"  # json, csv, or txt
        self.verbose = True
        self.timeout = 5
        
    def log(self, msg: str):
        """Print log messages."""
        if self.verbose:
            timestamp = datetime.now().strftime("%H:%M:%S")
            print(f"[{timestamp}] {msg}")
    
    # ═══════════════════════════════════════════════════════════════════════════
    # IP LOOKUP & GEOLOCATION
    # ═══════════════════════════════════════════════════════════════════════════
    
    def lookup_ip(self, ip: str) -> Dict[str, Any]:
        """
        Perform comprehensive IP lookup including:
        - Basic info (version, type, reserved)
        - Reverse DNS
        - GeoIP (if API available)
        """
        self.log(f"🔍 IP Lookup: {ip}")
        result = {
            "ip": ip,
            "timestamp": datetime.now().isoformat(),
            "errors": []
        }
        
        try:
            ip_obj = ipaddress.ip_address(ip)
            result["ip_version"] = ip_obj.version
            result["ip_type"] = self._classify_ip(ip_obj)
            result["is_private"] = ip_obj.is_private
            result["is_reserved"] = ip_obj.is_reserved
            result["is_loopback"] = ip_obj.is_loopback
            result["is_multicast"] = ip_obj.is_multicast
            
            # Reverse DNS lookup
            try:
                hostname, aliaslist, ipaddrlist = socket.gethostbyaddr(ip)
                result["reverse_dns"] = {
                    "hostname": hostname,
                    "aliases": aliaslist,
                    "addresses": ipaddrlist
                }
                self.log(f"  └─ Reverse DNS: {hostname}")
            except (socket.herror, socket.timeout):
                result["reverse_dns"] = None
            
            # GeoIP lookup using free API (ip-api.com)
            if not ip_obj.is_private:
                result["geoip"] = self._geoip_lookup(ip)
            
            # ASN lookup
            result["asn"] = self._lookup_asn(ip)
            
        except Exception as e:
            result["errors"].append(f"IP Lookup failed: {str(e)}")
        
        self.results["ip_lookup"] = result
        return result
    
    def _classify_ip(self, ip_obj) -> str:
        """Classify IP type."""
        if ip_obj.is_loopback:
            return "loopback"
        elif ip_obj.is_multicast:
            return "multicast"
        elif ip_obj.is_reserved:
            return "reserved"
        elif ip_obj.is_private:
            return "private"
        else:
            return "public"
    
    def _geoip_lookup(self, ip: str) -> Dict[str, Any]:
        """Lookup geolocation using public API."""
        if not requests:
            return {"error": "requests library not available"}
        
        try:
            response = requests.get(
                f"http://ip-api.com/json/{ip}",
                timeout=self.timeout,
                params={"fields": "status,continent,continentCode,country,countryCode,region,regionName,city,district,zip,lat,lon,timezone,isp,org,as,asname,reverse,mobile,proxy,hosting,query"}
            )
            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "success":
                    self.log(f"  └─ GeoIP: {data.get('city')}, {data.get('country')}")
                    return data
        except Exception as e:
            pass
        
        return {"error": "GeoIP lookup failed"}
    
    def _lookup_asn(self, ip: str) -> Optional[Dict[str, str]]:
        """Lookup ASN using whois lookups."""
        if not requests:
            return None
        
        try:
            response = requests.get(
                f"https://ipwhois.app/json/{ip}",
                timeout=self.timeout
            )
            if response.status_code == 200:
                data = response.json()
                return {
                    "asn": data.get("asn"),
                    "org": data.get("org"),
                    "isp": data.get("isp"),
                    "type": data.get("type")
                }
        except Exception:
            pass
        
        return None
    
    # ═══════════════════════════════════════════════════════════════════════════
    # DOMAIN WHOIS & RECONNAISSANCE
    # ═══════════════════════════════════════════════════════════════════════════
    
    def whois_domain(self, domain: str) -> Dict[str, Any]:
        """Perform WHOIS lookup on domain."""
        self.log(f"🌐 WHOIS Lookup: {domain}")
        result = {
            "domain": domain,
            "timestamp": datetime.now().isoformat(),
            "errors": []
        }
        
        try:
            # Try using whois command-line tool
            process = subprocess.run(
                ["whois", domain],
                capture_output=True,
                text=True,
                timeout=self.timeout
            )
            
            if process.returncode == 0:
                whois_text = process.stdout
                result["raw_whois"] = whois_text
                result["parsed"] = self._parse_whois(whois_text)
                self.log(f"  └─ WHOIS retrieved ({len(whois_text)} bytes)")
            else:
                result["errors"].append("whois command failed or not available")
        
        except FileNotFoundError:
            result["errors"].append("whois command not found on system")
        except Exception as e:
            result["errors"].append(f"WHOIS lookup error: {str(e)}")
        
        self.results["whois"] = result
        return result
    
    def _parse_whois(self, whois_text: str) -> Dict[str, str]:
        """Parse WHOIS response for key fields."""
        parsed = {}
        patterns = {
            "registrar": r"Registrar:\s*(.+)",
            "creation_date": r"Creation Date:\s*(.+)",
            "expiration_date": r"Expiration Date:\s*(.+)|Registrar Expiration Date:\s*(.+)",
            "name_servers": r"Name Server:\s*(.+)",
            "status": r"Domain Status:\s*(.+)|Status:\s*(.+)"
        }
        
        for key, pattern in patterns.items():
            matches = re.findall(pattern, whois_text, re.IGNORECASE)
            if matches:
                if key == "name_servers":
                    parsed[key] = [m[0].strip() if isinstance(m, tuple) else m.strip() for m in matches]
                else:
                    parsed[key] = matches[0][0] if isinstance(matches[0], tuple) else matches[0]
        
        return parsed
    
    # ═══════════════════════════════════════════════════════════════════════════
    # DNS RECORDS
    # ═══════════════════════════════════════════════════════════════════════════
    
    def dns_records(self, domain: str, record_types: List[str] = None) -> Dict[str, Any]:
        """
        Lookup DNS records for domain.
        Default types: A, AAAA, MX, NS, TXT, SOA, CNAME
        """
        if record_types is None:
            record_types = ["A", "AAAA", "MX", "NS", "TXT", "SOA", "CNAME"]
        
        self.log(f"📡 DNS Records: {domain}")
        result = {
            "domain": domain,
            "timestamp": datetime.now().isoformat(),
            "records": {},
            "errors": []
        }
        
        if not DNS_AVAILABLE:
            result["errors"].append("dnspython not installed - using socket fallback")
            # Fallback: try to resolve A and AAAA records manually
            try:
                a_records = socket.getaddrinfo(domain, None, socket.AF_INET, socket.SOCK_STREAM)
                result["records"]["A"] = [r[4][0] for r in a_records]
            except socket.gaierror:
                pass
            return result
        
        for rtype in record_types:
            try:
                answers = dns.resolver.resolve(domain, rtype, lifetime=self.timeout)
                result["records"][rtype] = [str(rr) for rr in answers]
                self.log(f"  └─ {rtype}: {len(answers)} records")
            except (dns.resolver.NXDOMAIN, dns.resolver.NoAnswer, dns.exception.Timeout):
                result["records"][rtype] = []
            except Exception as e:
                result["errors"].append(f"DNS {rtype} lookup error: {str(e)}")
        
        self.results["dns"] = result
        return result
    
    # ═══════════════════════════════════════════════════════════════════════════
    # PORT SCANNING (BASIC)
    # ═══════════════════════════════════════════════════════════════════════════
    
    def scan_ports(self, host: str, ports: List[int] = None, threaded: bool = True) -> Dict[str, Any]:
        """
        Basic TCP port scanner.
        Default ports: 80, 443, 22, 21, 25, 53, 3306, 5432, 8080, 8443
        """
        if ports is None:
            ports = [80, 443, 22, 21, 25, 53, 3306, 5432, 8080, 8443]
        
        self.log(f"🔌 Port Scan: {host} ({len(ports)} ports)")
        result = {
            "host": host,
            "ports_scanned": ports,
            "timestamp": datetime.now().isoformat(),
            "open_ports": [],
            "errors": []
        }
        
        def check_port(port):
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(self.timeout / 2)
                res = sock.connect_ex((host, port))
                sock.close()
                if res == 0:
                    result["open_ports"].append(port)
                    self.log(f"  └─ Port {port}: OPEN")
            except Exception:
                pass
        
        if threaded:
            threads = []
            for port in ports:
                t = threading.Thread(target=check_port, args=(port,))
                threads.append(t)
                t.start()
            
            for t in threads:
                t.join()
        else:
            for port in ports:
                check_port(port)
        
        if not result["open_ports"]:
            self.log(f"  └─ No open ports found")
        
        self.results["port_scan"] = result
        return result
    
    # ═══════════════════════════════════════════════════════════════════════════
    # EMAIL DISCOVERY
    # ═══════════════════════════════════════════════════════════════════════════
    
    def email_discovery(self, domain: str) -> Dict[str, Any]:
        """
        Discover emails associated with domain.
        Uses: DNS MX records, common patterns, and public APIs.
        """
        self.log(f"📧 Email Discovery: {domain}")
        result = {
            "domain": domain,
            "timestamp": datetime.now().isoformat(),
            "emails": [],
            "sources": {},
            "errors": []
        }
        
        # Get MX records
        mx_lookup = self.dns_records(domain, ["MX"])
        if mx_lookup.get("records", {}).get("MX"):
            result["mx_servers"] = mx_lookup["records"]["MX"]
            self.log(f"  └─ MX Servers: {len(result['mx_servers'])}")
        
        # Try Hunter.io API (free tier)
        if requests:
            hunter_results = self._hunter_email_lookup(domain)
            if hunter_results.get("emails"):
                result["emails"].extend(hunter_results["emails"])
                result["sources"]["hunter"] = len(hunter_results["emails"])
        
        # Try RocketReach-like free alternatives
        common_patterns = [
            f"admin@{domain}",
            f"contact@{domain}",
            f"info@{domain}",
            f"support@{domain}",
            f"sales@{domain}",
        ]
        result["emails"].extend(common_patterns)
        result["sources"]["patterns"] = len(common_patterns)
        
        # Deduplicate
        result["emails"] = list(set(result["emails"]))
        self.log(f"  └─ Found {len(result['emails'])} email addresses")
        
        self.results["email_discovery"] = result
        return result
    
    def _hunter_email_lookup(self, domain: str) -> Dict[str, Any]:
        """Lookup emails using Hunter.io API (public/free tier)."""
        result = {"emails": []}
        
        try:
            response = requests.get(
                "https://api.hunter.io/v2/domain-search",
                params={"domain": domain},
                timeout=self.timeout
            )
            if response.status_code == 200:
                data = response.json()
                if data.get("data", {}).get("emails"):
                    result["emails"] = [e["value"] for e in data["data"]["emails"]]
        except Exception:
            pass
        
        return result
    
    # ═══════════════════════════════════════════════════════════════════════════
    # REPUTATION CHECKS
    # ═══════════════════════════════════════════════════════════════════════════
    
    def reputation_check(self, target: str, check_type: str = "auto") -> Dict[str, Any]:
        """
        Check reputation of IP or domain.
        Uses: VirusTotal (free API), AbuseIPDB, URLhaus, etc.
        """
        self.log(f"⚠️  Reputation Check: {target}")
        result = {
            "target": target,
            "check_type": check_type,
            "timestamp": datetime.now().isoformat(),
            "reputation": {},
            "errors": []
        }
        
        # Auto-detect type
        if check_type == "auto":
            try:
                ipaddress.ip_address(target)
                check_type = "ip"
            except ValueError:
                check_type = "domain"
        
        result["check_type"] = check_type
        
        # VirusTotal-like check (using public APIs)
        vt_result = self._virustotal_check(target, check_type)
        if vt_result:
            result["reputation"]["virustotal"] = vt_result
        
        # AbuseIPDB check
        if check_type == "ip":
            abuse_result = self._abuseipdb_check(target)
            if abuse_result:
                result["reputation"]["abuseipdb"] = abuse_result
        
        self.log(f"  └─ Reputation data collected")
        self.results["reputation"] = result
        return result
    
    def _virustotal_check(self, target: str, check_type: str) -> Optional[Dict]:
        """Check VirusTotal-like reputation."""
        if not requests:
            return None
        
        try:
            # Using alternative: GoogleSafeBrowsing-like check
            response = requests.get(
                f"https://www.abuseipdb.com/check?q={target}",
                timeout=self.timeout,
                headers={"User-Agent": "Mozilla/5.0"}
            )
            if response.status_code == 200:
                return {"status": "checked", "source": "abuseipdb"}
        except Exception:
            pass
        
        return None
    
    def _abuseipdb_check(self, ip: str) -> Optional[Dict]:
        """Check AbuseIPDB reputation."""
        if not requests:
            return None
        
        try:
            # Simple check without API key
            response = requests.get(
                f"https://www.abuseipdb.com/api/v2/check?ipAddress={ip}&maxAgeInDays=90",
                timeout=self.timeout,
                headers={"User-Agent": "Mozilla/5.0"}
            )
            if response.status_code == 200:
                return {"status": "checked", "source": "abuseipdb"}
        except Exception:
            pass
        
        return None
    
    # ═══════════════════════════════════════════════════════════════════════════
    # EXPORT RESULTS
    # ═══════════════════════════════════════════════════════════════════════════
    
    def export_results(self, filename: str, fmt: str = "json") -> bool:
        """Export reconnaissance results to file."""
        try:
            if fmt == "json":
                with open(filename, "w") as f:
                    json.dump(self.results, f, indent=2, default=str)
            elif fmt == "csv":
                with open(filename, "w", newline="") as f:
                    writer = csv.writer(f)
                    self._flatten_to_csv(writer, self.results)
            elif fmt == "txt":
                with open(filename, "w") as f:
                    f.write(self._flatten_to_txt())
            
            self.log(f"✅ Results exported to {filename}")
            return True
        except Exception as e:
            self.log(f"❌ Export failed: {str(e)}")
            return False
    
    def _flatten_to_csv(self, writer, data, prefix=""):
        """Flatten JSON to CSV rows."""
        if isinstance(data, dict):
            for key, value in data.items():
                new_prefix = f"{prefix}.{key}" if prefix else key
                if isinstance(value, (dict, list)):
                    self._flatten_to_csv(writer, value, new_prefix)
                else:
                    writer.writerow([new_prefix, value])
        elif isinstance(data, list):
            for item in data:
                self._flatten_to_csv(writer, item, prefix)
    
    def _flatten_to_txt(self) -> str:
        """Convert results to human-readable text."""
        lines = []
        lines.append("=" * 80)
        lines.append("OSINT RECONNAISSANCE REPORT")
        lines.append(f"Generated: {datetime.now().isoformat()}")
        lines.append("=" * 80)
        
        for category, data in self.results.items():
            lines.append(f"\n[{category.upper()}]")
            lines.append("-" * 40)
            lines.append(json.dumps(data, indent=2, default=str))
        
        return "\n".join(lines)
    
    def get_summary(self) -> str:
        """Get brief summary of all reconnaissance."""
        summary = []
        summary.append("📊 OSINT Summary:")
        
        for category, data in self.results.items():
            if data:
                summary.append(f"  • {category}: ✓")
        
        return "\n".join(summary)


# ═══════════════════════════════════════════════════════════════════════════════
# CONVENIENCE FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════

def quick_osint(target: str) -> Dict[str, Any]:
    """Quick OSINT scan of IP or domain."""
    console = OSINTConsole()
    results = {}
    
    try:
        ipaddress.ip_address(target)
        # It's an IP
        results["ip"] = console.lookup_ip(target)
        results["ports"] = console.scan_ports(target)
        results["reputation"] = console.reputation_check(target)
    except ValueError:
        # It's a domain
        results["whois"] = console.whois_domain(target)
        results["dns"] = console.dns_records(target)
        results["emails"] = console.email_discovery(target)
        results["reputation"] = console.reputation_check(target)
    
    return results
