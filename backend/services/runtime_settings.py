from typing import Dict

from database import RuntimeSetting


class RuntimeSettingsStore:
    def __init__(self, session_factory):
        self.session_factory = session_factory

    def load(self) -> Dict[str, str]:
        db = self.session_factory()
        try:
            return {item.key: item.value for item in db.query(RuntimeSetting).all()}
        finally:
            db.close()

    def save(self, values: Dict[str, str]) -> None:
        db = self.session_factory()
        try:
            for key, value in values.items():
                item = db.query(RuntimeSetting).filter(RuntimeSetting.key == key).first()
                if item:
                    item.value = value
                else:
                    db.add(RuntimeSetting(key=key, value=value))
            db.commit()
        finally:
            db.close()

    def apply(self, ai_service, tts_service) -> None:
        values = self.load()
        ai_service.provider = values.get("ai.provider", ai_service.provider)
        ai_service.api_key = values.get("ai.api_key", ai_service.api_key)
        ai_service.base_url = values.get("ai.base_url", ai_service.base_url)
        ai_service.model = values.get("ai.model", ai_service.model)
        if values.get("ai.system_prompt", "").strip():
            ai_service.set_system_prompt(values["ai.system_prompt"])
        tts_service.voice = values.get("tts.voice", tts_service.voice)
        tts_service.rate = values.get("tts.rate", tts_service.rate)
        tts_service.pitch = values.get("tts.pitch", tts_service.pitch)
