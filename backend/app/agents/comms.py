"""Comms Agent: drafts public-address (PA) announcements in English and Hindi and SMS
alerts to shift supervisors whenever the evacuation picture changes."""
from __future__ import annotations

from .base import Agent, system_base

MIN_GAP = 8  # sim-seconds between announcements

HAZ_HI = {"fire": "आग", "gas": "गैस रिसाव", "smoke": "धुआँ"}


class CommsAgent(Agent):
    name = "Comms"

    def __init__(self, engine):
        super().__init__(engine)
        self.last_sig = None
        self.last_t = -999
        self.pending = False
        self.announced_clear = False

    def _signature(self):
        inc = self.inc
        return (inc["stage"], tuple(sorted(inc["evac_zones"])), tuple(sorted(inc["blocked_exits"])),
                tuple(sorted(inc["unsafe_aps"])), inc["all_clear_t"] is not None)

    def _context(self):
        e, inc = self.e, self.inc
        hz_kinds = {}
        for a in inc["alarms"].values():  # detector evidence first, refined by assessment below
            if a["zone"] is not None and a["state"] in ("alarm", "A2") and a["type"] != "smoke":
                hz_kinds[a["zone"]] = "fire" if a["type"] == "flame" else "gas"
        for z, h in inc["zone_hazards"].items():
            k = "fire" if "fire_m2" in h else "gas" if "gas_max_lel" in h else "smoke"
            hz_kinds[z] = k
        aps = [ap for ap in e.layout["assembly_points"] if ap["id"] not in inc["unsafe_aps"]]
        return {
            "stage": inc["stage"],
            "site": inc["site_evac"],
            "hazards": {self.zname(z): k for z, k in hz_kinds.items()},
            "evac_zones": [self.zname(z) for z in sorted(inc["evac_zones"]) if z != "corridor"],
            "blocked_exits": sorted(inc["blocked_exits"]),
            "unsafe_aps": [ap["name"] for ap in e.layout["assembly_points"] if ap["id"] in inc["unsafe_aps"]],
            "safe_aps": [ap["name"] for ap in aps],
            "all_clear": inc["all_clear_t"] is not None,
            "headcount": e.headcount(),
        }

    def _template(self, c: dict) -> dict:
        haz_en = ", ".join(f"{k} in {z}" for z, k in c["hazards"].items()) or "an emergency"
        haz_hi = ", ".join(f"{z} में {HAZ_HI[k]}" for z, k in c["hazards"].items()) or "आपात स्थिति"
        aps = " or ".join(c["safe_aps"]) or "the nearest safe open area"
        aps_hi = " या ".join(c["safe_aps"]) or "नज़दीकी सुरक्षित खुले स्थान"
        blocked = f" Do not use exit {', '.join(c['blocked_exits'])}." if c["blocked_exits"] else ""
        blocked_hi = f" एग्ज़िट {', '.join(c['blocked_exits'])} का उपयोग न करें।" if c["blocked_exits"] else ""
        unsafe = f" {', '.join(c['unsafe_aps'])} is closed." if c["unsafe_aps"] else ""
        unsafe_hi = f" {', '.join(c['unsafe_aps'])} बंद है।" if c["unsafe_aps"] else ""
        hc = c["headcount"]
        if c["all_clear"]:
            en = (f"Attention please. All personnel from the evacuated areas are accounted for. Remain at your "
                  f"assembly point and follow instructions from your wardens.")
            hi = "ध्यान दें। खाली कराए गए क्षेत्रों के सभी कर्मचारी सुरक्षित हैं। अपने असेंबली पॉइंट पर रहें और वार्डन के निर्देशों का पालन करें।"
        elif c["site"]:
            en = (f"Emergency, emergency. {haz_en.capitalize()}. This is a full site evacuation. All personnel, "
                  f"contractors and visitors leave immediately by the routes shown and go to {aps}.{blocked}{unsafe} Do not run.")
            hi = (f"आपातकाल, आपातकाल। {haz_hi}। पूरा प्लांट खाली करें। सभी कर्मचारी, ठेकेदार और आगंतुक तुरंत "
                  f"दिखाए गए रास्ते से {aps_hi} पर पहुँचें।{blocked_hi}{unsafe_hi} दौड़ें नहीं।")
        elif c["stage"] >= 2:
            zones = ", ".join(c["evac_zones"])
            en = (f"Attention. {haz_en.capitalize()}. Personnel in {zones} evacuate now and go to {aps}.{blocked}{unsafe} "
                  f"All other areas stand by.")
            hi = (f"ध्यान दें। {haz_hi}। {zones} के सभी कर्मचारी तुरंत बाहर निकलें और {aps_hi} पर पहुँचें।"
                  f"{blocked_hi}{unsafe_hi} बाकी क्षेत्र तैयार रहें।")
        else:
            en = "Attention. An alarm is being investigated by the Emergency Response Team. Stay alert and await instructions."
            hi = "ध्यान दें। एक अलार्म की जाँच की जा रही है। सतर्क रहें और निर्देशों का इंतज़ार करें।"
        sms = (f"EVACTIVE {'ALL CLEAR' if c['all_clear'] else 'STAGE ' + str(c['stage'])}: {haz_en}. "
               f"Safe {hc['safe']}/{hc['total']}, moving {hc['evacuating']}, trapped {hc['trapped']}, injured {hc['injured']}."
               + (f" Blocked: {', '.join(c['blocked_exits'])}." if c["blocked_exits"] else ""))
        return {"en": en, "hi": hi, "sms": sms[:300]}

    @staticmethod
    def _parse(text: str):
        out = {}
        for line in text.splitlines():
            line = line.strip().strip("*").strip()
            for key in ("EN", "HI", "SMS"):
                if line.upper().startswith(key + ":"):
                    out[key.lower()] = line.split(":", 1)[1].strip().strip('"')
        return out if {"en", "hi", "sms"} <= out.keys() else None

    def _announce(self, t: int):
        self.pending = True
        self.last_t = t
        c = self._context()
        tpl = self._template(c)
        sys = system_base(self.e) + " You are the Comms Agent writing public-address announcements and SMS alerts."
        prompt = ("Write three lines exactly in this format:\n"
                  "EN: <PA announcement in English, max 45 words, calm and directive>\n"
                  "HI: <the same announcement in Hindi (Devanagari)>\n"
                  "SMS: <alert to shift supervisors, max 160 characters, include headcount>\n\n"
                  f"FACTS: {c}\n\nReference wording you may improve (keep all facts):\nEN: {tpl['en']}\nHI: {tpl['hi']}\nSMS: {tpl['sms']}")

        def done(text: str, llm: bool):
            self.pending = False
            msg = self._parse(text) if llm else None
            if msg is None:
                msg, llm = tpl, False
            self.inc["pa"] = {"t": self.e.t, "en": msg["en"], "hi": msg["hi"], "llm": llm}
            self.inc["sms"].append({"t": self.e.t, "text": msg["sms"], "llm": llm})
            self.log(f"PA (EN): {msg['en']}", "info", llm=llm, kind="pa")
            self.log(f"PA (HI): {msg['hi']}", "info", llm=llm, kind="pa")
            self.log(f"SMS to shift supervisors: {msg['sms']}", "info", llm=llm, kind="sms")

        self.e.spawn_llm(lambda: self.e.llm.chat(sys, prompt, 320), done, lambda: "")

    def step(self, t: int):
        sig = self._signature()
        if sig == self.last_sig or self.pending or self.inc["stage"] == 0:
            return
        if t - self.last_t < MIN_GAP:
            return
        self.last_sig = sig
        self._announce(t)
