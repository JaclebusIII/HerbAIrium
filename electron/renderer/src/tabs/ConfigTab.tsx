import {
  forwardRef,
  useEffect,
  useImperativeHandle,
  useMemo,
  useRef,
  useState,
} from "react";
import { saveConfig } from "../api";
import { useApp } from "../context/AppContext";
import type { Configuration } from "../types";

export interface ConfigTabHandle {
  isSaving: () => boolean;
  save: () => Promise<boolean>;
}

interface ConfigTabProps {
  onDirtyChange: (dirty: boolean) => void;
  onSavingChange: (saving: boolean) => void;
}

const editableKeys = [
  "llm_base_url",
  "deepinfra_api_key",
  "olm_model",
  "olm_temperature",
  "olm_max_tokens",
  "olm_prompt",
  "llm_parse_model",
  "llm_parse_temperature",
  "llm_parse_max_tokens",
  "llm_parse_prompt",
] as const satisfies readonly (keyof Configuration)[];

export const ConfigTab = forwardRef<ConfigTabHandle, ConfigTabProps>(function ConfigTab(
  { onDirtyChange, onSavingChange },
  ref,
) {
  const { config, setConfig } = useApp();
  if (!config) return null;

  const [form, setForm] = useState<Configuration>({ ...config });
  const [status, setStatus] = useState<{ ok: boolean; msg: string } | null>(null);
  const [saving, setSaving] = useState(false);
  const savePromiseRef = useRef<Promise<boolean> | null>(null);
  const isDirty = useMemo(
    () => editableKeys.some((key) => form[key] !== config[key]),
    [config, form],
  );

  useEffect(() => {
    onDirtyChange(isDirty);
  }, [isDirty, onDirtyChange]);

  useEffect(() => () => onDirtyChange(false), [onDirtyChange]);

  function update(key: keyof Configuration, value: string | number) {
    setForm((prev) => ({ ...prev, [key]: value }));
  }

  function handleSave(): Promise<boolean> {
    if (savePromiseRef.current) return savePromiseRef.current;

    const savePromise = (async () => {
      onSavingChange(true);
      setSaving(true);
      setStatus(null);
      try {
        // eslint-disable-next-line @typescript-eslint/no-unused-vars
        const { image_files: _files, ...saveable } = form;
        await saveConfig(saveable);
        setConfig({ ...form });
        setStatus({ ok: true, msg: "Saved." });
        return true;
      } catch (err) {
        setStatus({ ok: false, msg: err instanceof Error ? err.message : String(err) });
        return false;
      } finally {
        setSaving(false);
        onSavingChange(false);
        savePromiseRef.current = null;
      }
    })();

    savePromiseRef.current = savePromise;
    return savePromise;
  }

  useImperativeHandle(ref, () => ({
    isSaving: () => savePromiseRef.current !== null,
    save: handleSave,
  }));

  return (
    <div className="p-4 overflow-y-auto h-full">
      <h2 className="text-xl font-semibold mb-4">Configuration</h2>

      <fieldset disabled={saving}>
        <Field label="LLM base URL">
          <input
            className={inputCls}
            value={form.llm_base_url}
            onChange={(e) => update("llm_base_url", e.target.value)}
          />
        </Field>

        <Field label="API key">
          <input
            className={inputCls}
            type="password"
            value={form.deepinfra_api_key}
            onChange={(e) => update("deepinfra_api_key", e.target.value)}
          />
        </Field>

        <hr className="my-4" />
        <h3 className="font-semibold mb-2">VLM / OCR</h3>

        <Field label="OCR model">
          <input
            className={inputCls}
            value={form.olm_model}
            onChange={(e) => update("olm_model", e.target.value)}
          />
        </Field>

        <Field label={`OCR temperature: ${form.olm_temperature}`}>
          <input
            type="range"
            min={0}
            max={2}
            step={0.1}
            value={form.olm_temperature}
            onChange={(e) => update("olm_temperature", parseFloat(e.target.value))}
            className="w-full"
          />
        </Field>

        <Field label="OCR max tokens">
          <input
            className={inputCls}
            type="number"
            value={form.olm_max_tokens}
            onChange={(e) => update("olm_max_tokens", parseInt(e.target.value, 10))}
          />
        </Field>

        <Field label="OCR prompt">
          <textarea
            className={`${inputCls} h-28`}
            value={form.olm_prompt}
            onChange={(e) => update("olm_prompt", e.target.value)}
          />
        </Field>

        <hr className="my-4" />
        <h3 className="font-semibold mb-2">LLM Parse</h3>

        <Field label="Parse model">
          <input
            className={inputCls}
            value={form.llm_parse_model}
            onChange={(e) => update("llm_parse_model", e.target.value)}
          />
        </Field>

        <Field label={`Parse temperature: ${form.llm_parse_temperature}`}>
          <input
            type="range"
            min={0}
            max={2}
            step={0.1}
            value={form.llm_parse_temperature}
            onChange={(e) => update("llm_parse_temperature", parseFloat(e.target.value))}
            className="w-full"
          />
        </Field>

        <Field label="Parse max tokens">
          <input
            className={inputCls}
            type="number"
            value={form.llm_parse_max_tokens}
            onChange={(e) => update("llm_parse_max_tokens", parseInt(e.target.value, 10))}
          />
        </Field>

        <Field label="Parse prompt">
          <textarea
            className={`${inputCls} h-48`}
            value={form.llm_parse_prompt}
            onChange={(e) => update("llm_parse_prompt", e.target.value)}
          />
        </Field>

        <button
          className="mt-4 px-4 py-2 bg-green-600 text-white rounded-lg text-sm font-medium hover:bg-green-700 disabled:opacity-50"
          onClick={handleSave}
          disabled={saving}
        >
          {saving ? "Saving…" : "Save configuration"}
        </button>
      </fieldset>

      {status && (
        <p className={`mt-2 text-sm ${status.ok ? "text-green-700" : "text-red-600"}`}>
          {status.msg}
        </p>
      )}
    </div>
  );
});

const inputCls =
  "w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-green-500";

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="mb-3">
      <label className="block text-sm font-medium text-gray-700 mb-1">{label}</label>
      {children}
    </div>
  );
}
