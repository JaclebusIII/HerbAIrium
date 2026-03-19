import flet as ft

from .state import AppState


def build_config_tab(page: ft.Page, state: AppState) -> ft.Control:
    cfg = state.configuration
    assert cfg is not None

    base_url = ft.TextField(label="LLM base URL", value=cfg.llm_base_url, expand=True)
    api_key = ft.TextField(
        label="API key",
        value=cfg.deepinfra_api_key,
        password=True,
        can_reveal_password=True,
        expand=True,
    )
    olm_model = ft.TextField(label="VLM / OCR model", value=cfg.olm_model, expand=True)
    olm_temp = ft.Slider(label="OCR temperature", min=0, max=2, divisions=20, value=cfg.olm_temperature)
    olm_tokens = ft.TextField(
        label="OCR max tokens",
        value=str(cfg.olm_max_tokens),
        keyboard_type=ft.KeyboardType.NUMBER,
    )
    olm_prompt = ft.TextField(
        label="OCR prompt",
        value=cfg.olm_prompt,
        multiline=True,
        min_lines=4,
        max_lines=12,
        expand=True,
    )
    parse_model = ft.TextField(label="Parse model", value=cfg.llm_parse_model, expand=True)
    parse_temp = ft.Slider(
        label="Parse temperature", min=0, max=2, divisions=20, value=cfg.llm_parse_temperature
    )
    parse_tokens = ft.TextField(
        label="Parse max tokens",
        value=str(cfg.llm_parse_max_tokens),
        keyboard_type=ft.KeyboardType.NUMBER,
    )
    parse_prompt = ft.TextField(
        label="Parse prompt",
        value=cfg.llm_parse_prompt,
        multiline=True,
        min_lines=6,
        max_lines=20,
        expand=True,
    )
    save_msg = ft.Text()

    def save_config(_):
        try:
            cfg.llm_base_url = base_url.value or cfg.llm_base_url
            cfg.deepinfra_api_key = api_key.value or ""
            cfg.olm_model = olm_model.value or cfg.olm_model
            cfg.olm_temperature = float(olm_temp.value)
            cfg.olm_max_tokens = int(olm_tokens.value or "4096")
            cfg.olm_prompt = olm_prompt.value or cfg.olm_prompt
            cfg.llm_parse_model = parse_model.value or cfg.llm_parse_model
            cfg.llm_parse_temperature = float(parse_temp.value)
            cfg.llm_parse_max_tokens = int(parse_tokens.value or "4096")
            cfg.llm_parse_prompt = parse_prompt.value or cfg.llm_parse_prompt
        except ValueError as e:
            save_msg.value = str(e)
            save_msg.color = ft.Colors.ERROR
            page.update()
            return
        ok = cfg.save()
        save_msg.value = "Saved." if ok else "Save failed."
        save_msg.color = ft.Colors.GREEN if ok else ft.Colors.ERROR
        page.update()

    return ft.Container(
        content=ft.Column(
            [
                ft.Text("Configuration", size=22, weight=ft.FontWeight.W_600),
                base_url,
                api_key,
                ft.Divider(),
                ft.Text("VLM OCR", weight=ft.FontWeight.W_600),
                olm_model,
                olm_temp,
                olm_tokens,
                olm_prompt,
                ft.Divider(),
                ft.Text("LLM parse", weight=ft.FontWeight.W_600),
                parse_model,
                parse_temp,
                parse_tokens,
                parse_prompt,
                ft.FilledButton("Save configuration", icon=ft.Icons.SAVE, on_click=save_config),
                save_msg,
            ],
            spacing=12,
            scroll=ft.ScrollMode.AUTO,
        ),
        padding=16,
    )
