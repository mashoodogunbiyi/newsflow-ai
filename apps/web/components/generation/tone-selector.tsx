import { GENERATION_TONES, type GenerationTone } from "@/types/generation";

type ToneSelectorProps = {
  disabled?: boolean;
  onChange: (value: GenerationTone) => void;
  value: GenerationTone;
};

export function ToneSelector({ disabled = false, onChange, value }: ToneSelectorProps) {
  return (
    <fieldset className="min-w-0" disabled={disabled}>
      <legend className="text-base font-semibold text-emerald-950">Writing tone</legend>
      <p className="mt-1 text-sm leading-6 text-emerald-950/70" id="tone-description">
        Choose how the draft should sound. FastAPI will validate this choice again.
      </p>
      <div aria-describedby="tone-description" className="mt-4 grid gap-3 sm:grid-cols-3">
        {GENERATION_TONES.map((option) => (
          <label
            className="group relative flex cursor-pointer gap-3 rounded-2xl border border-emerald-950/15 bg-white p-4 transition hover:border-emerald-700/40 has-checked:border-emerald-700 has-checked:bg-emerald-50/70 has-focus-visible:outline-2 has-focus-visible:outline-offset-2 has-focus-visible:outline-emerald-700 has-disabled:cursor-not-allowed has-disabled:opacity-55"
            key={option.value}
          >
            <input
              checked={value === option.value}
              className="mt-1 h-4 w-4 shrink-0 accent-emerald-800"
              name="generation-tone"
              onChange={() => onChange(option.value)}
              type="radio"
              value={option.value}
            />
            <span>
              <span className="block text-sm font-semibold text-emerald-950">{option.label}</span>
              <span className="mt-1 block text-xs leading-5 text-emerald-950/70">
                {option.description}
              </span>
            </span>
          </label>
        ))}
      </div>
    </fieldset>
  );
}
