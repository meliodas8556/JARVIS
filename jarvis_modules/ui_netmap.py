from __future__ import annotations

import threading
import time
from typing import Any

import tkinter as tk


def build_netmap_widget(app: Any, parent: Any) -> None:
    tk.Frame(parent, bg="#0a3d52", height=1).pack(fill="x", pady=(8, 4), padx=4)
    netmap_frame = tk.Frame(parent, bg="#03101a")
    netmap_frame.pack(anchor="e", fill="x")
    tk.Label(netmap_frame, text="◈ NETWORK MAP", bg="#03101a", fg="#00e5ff", font=("Consolas", 8, "bold")).pack(anchor="e")

    app.netmap_canvas = tk.Canvas(
        netmap_frame,
        bg="#020d16",
        width=290,
        height=58,
        highlightthickness=1,
        highlightbackground="#0a3d52",
        bd=0,
    )
    app.netmap_canvas.pack(anchor="e", pady=(2, 3))

    app.netmap_ip_var = tk.StringVar(value="IP : détection...")
    app.netmap_gw_var = tk.StringVar(value="GW : ...")
    app.netmap_public_ip_var = tk.StringVar(value="IP publique : détection...")
    app.netmap_country_var = tk.StringVar(value="Pays sortie : ...")
    app.netmap_vpn_var = tk.StringVar(value="VPN : analyse...")
    app.netmap_iface_var = tk.StringVar(value="Interface : ...")
    app.netmap_os_var = tk.StringVar(value=f"OS : {app.user_os}")

    tk.Label(netmap_frame, textvariable=app.netmap_os_var, bg="#03101a", fg="#69ff8a", font=("Consolas", 9, "bold")).pack(anchor="e")
    tk.Label(netmap_frame, textvariable=app.netmap_ip_var, bg="#03101a", fg="#72ffb2", font=("Consolas", 9, "bold")).pack(anchor="e")
    tk.Label(netmap_frame, textvariable=app.netmap_gw_var, bg="#03101a", fg="#72b6ff", font=("Consolas", 9)).pack(anchor="e")
    tk.Label(netmap_frame, textvariable=app.netmap_public_ip_var, bg="#03101a", fg="#ffd166", font=("Consolas", 9, "bold")).pack(anchor="e")
    tk.Label(netmap_frame, textvariable=app.netmap_country_var, bg="#03101a", fg="#ff9f6e", font=("Consolas", 9)).pack(anchor="e")
    tk.Label(netmap_frame, textvariable=app.netmap_vpn_var, bg="#03101a", fg="#fca5ff", font=("Consolas", 9, "bold")).pack(anchor="e")
    tk.Label(netmap_frame, textvariable=app.netmap_iface_var, bg="#03101a", fg="#9ad3ff", font=("Consolas", 9)).pack(anchor="e")

    vpn_btn_frame = tk.Frame(netmap_frame, bg="#03101a")
    vpn_btn_frame.pack(anchor="e", pady=(5, 0))
    app.vpn_test_btn = tk.Button(
        vpn_btn_frame,
        text="⟳ Tester le VPN",
        bg="#0a2535",
        fg="#00e5ff",
        activebackground="#0d3550",
        activeforeground="#ffffff",
        font=("Consolas", 9, "bold"),
        relief="flat",
        bd=0,
        padx=10,
        pady=4,
        cursor="hand2",
        command=app._force_netmap_refresh,
    )
    app.vpn_test_btn.pack(side="right")
    app.root.after(400, app._refresh_netmap)
    app.root.after(600, app._animate_netmap)


def draw_netmap(app: Any, local_ip: str, gateway: str) -> None:
    if not hasattr(app, "netmap_canvas"):
        return
    canvas = app.netmap_canvas
    canvas.delete("all")
    width, height = 290, 58

    for x in range(0, width, 20):
        canvas.create_line(x, 0, x, height, fill="#051421", width=1)
    for y in range(0, height, 20):
        canvas.create_line(0, y, width, y, fill="#051421", width=1)

    canvas.create_rectangle(6, 14, 72, 38, fill="#0a2535", outline="#00a8cc", width=1)
    canvas.create_text(39, 26, text="PC", fill="#00e5ff", font=("Consolas", 8, "bold"))
    short_ip = ".".join(local_ip.split(".")[-2:]) if "." in local_ip else local_ip
    canvas.create_text(39, 50, text=short_ip, fill="#3a8fa8", font=("Consolas", 7))

    canvas.create_line(72, 26, 116, 26, fill="#007da0", width=2, dash=(4, 2))
    phase = int(time.monotonic() * 4) % 4
    dot_x = 76 + phase * 10
    canvas.create_oval(dot_x - 3, 23, dot_x + 3, 29, fill="#00e5ff", outline="")

    gw_label = gateway[:9] if gateway not in ("N/A", "") else "???"
    canvas.create_rectangle(116, 14, 188, 38, fill="#0a251a", outline="#00cc88", width=1)
    canvas.create_text(152, 26, text="GW", fill="#69ff8a", font=("Consolas", 8, "bold"))
    canvas.create_text(152, 50, text=gw_label, fill="#2a8a60", font=("Consolas", 7))

    canvas.create_line(188, 26, 232, 26, fill="#007a44", width=2, dash=(4, 2))
    dot2_x = 192 + ((phase + 2) % 4) * 10
    canvas.create_oval(dot2_x - 3, 23, dot2_x + 3, 29, fill="#69ff8a", outline="")

    canvas.create_rectangle(232, 14, 284, 38, fill="#251010", outline="#cc4444", width=1)
    canvas.create_text(258, 26, text="WAN", fill="#ff7070", font=("Consolas", 8, "bold"))
    canvas.create_text(258, 50, text="internet", fill="#7a3030", font=("Consolas", 7))


def refresh_netmap(app: Any) -> None:
    def worker():
        local_ip = app._get_local_ip()
        gateway = app._get_gateway_ip()
        interface_name = app._get_active_network_interface(local_ip)
        public_info = app._get_public_network_info()
        vpn_info = app._detect_vpn_status(local_ip, interface_name)
        payload = {
            "local_ip": local_ip,
            "gateway": gateway,
            "interface": interface_name,
            "public_ip": str(public_info.get("public_ip", "indisponible")),
            "country": str(public_info.get("country", "inconnu")),
            "country_code": str(public_info.get("country_code", "--")),
            "city": str(public_info.get("city", "")),
            "org": str(public_info.get("org", "")),
            "vpn_active": bool(vpn_info.get("active", False)),
            "vpn_label": str(vpn_info.get("label", "aucun")),
        }
        app.worker_queue.put(("netmap_update", payload))

    threading.Thread(target=worker, daemon=True).start()
    try:
        if app.root.winfo_exists():
            app.root.after(app.netmap_refresh_interval_ms, app._refresh_netmap)
    except Exception:
        pass


def force_netmap_refresh(app: Any) -> None:
    if hasattr(app, "vpn_test_btn"):
        app.vpn_test_btn.configure(state="disabled", text="⟳ Analyse...")
    app._append_terminal_output("[VPN TEST] Détection de la sortie réseau en cours...", "term_header")

    def worker():
        local_ip = app._get_local_ip()
        gateway = app._get_gateway_ip()
        interface_name = app._get_active_network_interface(local_ip)
        public_info = app._get_public_network_info()
        vpn_info = app._detect_vpn_status(local_ip, interface_name)
        payload = {
            "local_ip": local_ip,
            "gateway": gateway,
            "interface": interface_name,
            "public_ip": str(public_info.get("public_ip", "indisponible")),
            "country": str(public_info.get("country", "inconnu")),
            "country_code": str(public_info.get("country_code", "--")),
            "city": str(public_info.get("city", "")),
            "org": str(public_info.get("org", "")),
            "vpn_active": bool(vpn_info.get("active", False)),
            "vpn_label": str(vpn_info.get("label", "aucun")),
        }
        app.worker_queue.put(("netmap_update", payload))
        app.worker_queue.put(("netmap_test_done", payload))

    threading.Thread(target=worker, daemon=True).start()


def animate_netmap(app: Any) -> None:
    if hasattr(app, "netmap_canvas"):
        local_ip, gateway = app._netmap_last_data
        draw_netmap(app, local_ip, gateway)
    try:
        if app.root.winfo_exists():
            app.root.after(app.netmap_anim_interval_ms, app._animate_netmap)
    except Exception:
        pass
