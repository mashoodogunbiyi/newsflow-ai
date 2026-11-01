import {
  IMAGE_ASPECT_RATIOS,
  IMAGE_COMPOSITIONS,
  IMAGE_STYLES,
  type ImageAspectRatio,
  type ImageComposition,
  type ImageStyle,
} from "@/types/image-generation";

type ImagePreferenceControlsProps = {
  aspectRatio: ImageAspectRatio;
  composition: ImageComposition;
  disabled: boolean;
  onAspectRatioChange: (value: ImageAspectRatio) => void;
  onCompositionChange: (value: ImageComposition) => void;
  onStyleChange: (value: ImageStyle) => void;
  style: ImageStyle;
};

export function ImagePreferenceControls({
  aspectRatio,
  composition,
  disabled,
  onAspectRatioChange,
  onCompositionChange,
  onStyleChange,
  style,
}: ImagePreferenceControlsProps) {
  return (
    <div className="space-y-5">
      <fieldset disabled={disabled}>
        <legend className="text-sm font-semibold text-emerald-950">Illustration style</legend>
        <div className="mt-3 grid gap-3 sm:grid-cols-2" role="radiogroup">
          {IMAGE_STYLES.map((option) => (
            <label
              className={`cursor-pointer rounded-2xl border p-3 transition focus-within:outline-2 focus-within:outline-offset-2 focus-within:outline-emerald-700 ${
                style === option.value
                  ? "border-emerald-700 bg-emerald-50"
                  : "border-emerald-950/10 bg-white hover:border-emerald-950/25"
              }`}
              key={option.value}
            >
              <span className="flex items-start gap-3">
                <input
                  checked={style === option.value}
                  className="mt-1 accent-emerald-800"
                  name="image-style"
                  onChange={() => onStyleChange(option.value)}
                  type="radio"
                  value={option.value}
                />
                <span>
                  <span className="block text-sm font-semibold text-emerald-950">
                    {option.label}
                  </span>
                  <span className="mt-1 block text-xs leading-5 text-emerald-950/55">
                    {option.description}
                  </span>
                </span>
              </span>
            </label>
          ))}
        </div>
      </fieldset>

      <div className="grid gap-4 sm:grid-cols-2">
        <label className="text-sm font-semibold text-emerald-950">
          Image shape
          <select
            className="mt-2 min-h-11 w-full rounded-xl border border-emerald-950/15 bg-white px-3 text-sm font-normal text-emerald-950 focus:outline-2 focus:outline-offset-2 focus:outline-emerald-700"
            disabled={disabled}
            onChange={(event) => onAspectRatioChange(event.target.value as ImageAspectRatio)}
            value={aspectRatio}
          >
            {IMAGE_ASPECT_RATIOS.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </label>
        <label className="text-sm font-semibold text-emerald-950">
          Composition
          <select
            className="mt-2 min-h-11 w-full rounded-xl border border-emerald-950/15 bg-white px-3 text-sm font-normal text-emerald-950 focus:outline-2 focus:outline-offset-2 focus:outline-emerald-700"
            disabled={disabled}
            onChange={(event) => onCompositionChange(event.target.value as ImageComposition)}
            value={composition}
          >
            {IMAGE_COMPOSITIONS.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </label>
      </div>
    </div>
  );
}
