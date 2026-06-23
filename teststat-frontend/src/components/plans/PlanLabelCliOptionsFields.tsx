export interface LabelCliOptionsInput {
  targetSheets: string
  ignoreSheets: string
  includeHiddenSheets: '' | 'true' | 'false'
  targetEnvironments: string
  ignoreEnvironments: string
}

export function PlanLabelCliOptionsFields({
  value,
  disabled,
  onChange,
}: {
  value: LabelCliOptionsInput
  disabled: boolean
  onChange: (value: LabelCliOptionsInput) => void
}) {
  const update = (patch: Partial<LabelCliOptionsInput>) => onChange({ ...value, ...patch })

  return (
    <fieldset className="label-cli-options">
      <legend>集計オプション</legend>
      <div className="form-grid">
        <label>
          <span>対象シート target_sheets</span>
          <textarea
            value={value.targetSheets}
            disabled={disabled}
            onChange={(event) => update({ targetSheets: event.target.value })}
            placeholder={"テスト項目"}
            rows={3}
          />
        </label>
        <label>
          <span>除外シート ignore_sheets</span>
          <textarea
            value={value.ignoreSheets}
            disabled={disabled}
            onChange={(event) => update({ ignoreSheets: event.target.value })}
            placeholder={"Sheet1\n_temp"}
            rows={3}
          />
        </label>
        <label>
          <span>非表示シート include_hidden_sheets</span>
          <select
            value={value.includeHiddenSheets}
            disabled={disabled}
            onChange={(event) => update({ includeHiddenSheets: event.target.value as LabelCliOptionsInput['includeHiddenSheets'] })}
          >
            <option value="">config.json の設定を使用</option>
            <option value="true">含める</option>
            <option value="false">含めない</option>
          </select>
        </label>
        <label>
          <span>対象環境 target_environments</span>
          <textarea
            value={value.targetEnvironments}
            disabled={disabled}
            onChange={(event) => update({ targetEnvironments: event.target.value })}
            placeholder={"環境a"}
            rows={3}
          />
        </label>
        <label>
          <span>除外環境 ignore_environments</span>
          <textarea
            value={value.ignoreEnvironments}
            disabled={disabled}
            onChange={(event) => update({ ignoreEnvironments: event.target.value })}
            placeholder={""}
            rows={3}
          />
        </label>
      </div>
    </fieldset>
  )
}
