export interface BenefitsData {
  annual_maximum: string;
  annual_used: string;
  annual_remaining: string;
  deductible: string;
  deductible_met: boolean;
  preventive_coverage: string;
  basic_coverage: string;
  major_coverage: string;
  orthodontic_coverage: string;
  waiting_period_months: string;
  plan_effective_date: string;
}

export const DEFAULT_BENEFITS: BenefitsData = {
  annual_maximum: "",
  annual_used: "",
  annual_remaining: "",
  deductible: "",
  deductible_met: false,
  preventive_coverage: "100",
  basic_coverage: "80",
  major_coverage: "50",
  orthodontic_coverage: "0",
  waiting_period_months: "0",
  plan_effective_date: "",
};

interface BenefitsEntryProps {
  benefits: BenefitsData;
  onChange: (benefits: BenefitsData) => void;
}

function DollarField({
  label,
  value,
  field,
  onChange,
}: {
  label: string;
  value: string;
  field: string;
  onChange: (field: string, value: string) => void;
}) {
  return (
    <div>
      <label className="block text-xs font-heading text-gray-500 mb-1">
        {label}
      </label>
      <div className="relative">
        <span className="absolute left-2.5 top-1/2 -translate-y-1/2 text-gray-500 text-xs">
          $
        </span>
        <input
          type="text"
          inputMode="decimal"
          value={value}
          onChange={(e) => onChange(field, e.target.value)}
          className="input-field !pl-6"
          placeholder="0.00"
        />
      </div>
    </div>
  );
}

function PercentField({
  label,
  value,
  field,
  onChange,
}: {
  label: string;
  value: string;
  field: string;
  onChange: (field: string, value: string) => void;
}) {
  return (
    <div>
      <label className="block text-xs font-heading text-gray-500 mb-1">
        {label}
      </label>
      <div className="relative">
        <input
          type="text"
          inputMode="numeric"
          value={value}
          onChange={(e) => onChange(field, e.target.value)}
          className="input-field !pr-7"
          placeholder="0"
        />
        <span className="absolute right-2.5 top-1/2 -translate-y-1/2 text-gray-500 text-xs">
          %
        </span>
      </div>
    </div>
  );
}

export default function BenefitsEntry({ benefits, onChange }: BenefitsEntryProps) {
  function handleChange(field: string, value: string) {
    onChange({ ...benefits, [field]: value });
  }

  return (
    <div className="space-y-4">
      {/* Annual amounts */}
      <div>
        <p className="text-[10px] font-heading text-gray-500 uppercase tracking-wider mb-2">
          Annual Benefits
        </p>
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
          <DollarField
            label="Annual Maximum"
            value={benefits.annual_maximum}
            field="annual_maximum"
            onChange={handleChange}
          />
          <DollarField
            label="Used"
            value={benefits.annual_used}
            field="annual_used"
            onChange={handleChange}
          />
          <DollarField
            label="Remaining"
            value={benefits.annual_remaining}
            field="annual_remaining"
            onChange={handleChange}
          />
        </div>
      </div>

      {/* Deductible */}
      <div>
        <p className="text-[10px] font-heading text-gray-500 uppercase tracking-wider mb-2">
          Deductible
        </p>
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 items-end">
          <DollarField
            label="Deductible Amount"
            value={benefits.deductible}
            field="deductible"
            onChange={handleChange}
          />
          <div>
            <label className="block text-xs font-heading text-gray-500 mb-1">
              Deductible Met
            </label>
            <button
              type="button"
              onClick={() =>
                onChange({ ...benefits, deductible_met: !benefits.deductible_met })
              }
              className={`h-[38px] w-full rounded-lg border text-xs font-heading font-semibold transition-colors ${
                benefits.deductible_met
                  ? "bg-lime/10 border-lime/30 text-lime"
                  : "bg-navy-900 border-gray-600/40 text-gray-500"
              }`}
            >
              {benefits.deductible_met ? "Yes" : "No"}
            </button>
          </div>
        </div>
      </div>

      {/* Coverage percentages */}
      <div>
        <p className="text-[10px] font-heading text-gray-500 uppercase tracking-wider mb-2">
          Coverage Percentages
        </p>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          <PercentField
            label="Preventive"
            value={benefits.preventive_coverage}
            field="preventive_coverage"
            onChange={handleChange}
          />
          <PercentField
            label="Basic"
            value={benefits.basic_coverage}
            field="basic_coverage"
            onChange={handleChange}
          />
          <PercentField
            label="Major"
            value={benefits.major_coverage}
            field="major_coverage"
            onChange={handleChange}
          />
          <PercentField
            label="Orthodontic"
            value={benefits.orthodontic_coverage}
            field="orthodontic_coverage"
            onChange={handleChange}
          />
        </div>
      </div>

      {/* Plan details */}
      <div>
        <p className="text-[10px] font-heading text-gray-500 uppercase tracking-wider mb-2">
          Plan Details
        </p>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="block text-xs font-heading text-gray-500 mb-1">
              Waiting Period (months)
            </label>
            <input
              type="text"
              inputMode="numeric"
              value={benefits.waiting_period_months}
              onChange={(e) => handleChange("waiting_period_months", e.target.value)}
              className="input-field"
              placeholder="0"
            />
          </div>
          <div>
            <label className="block text-xs font-heading text-gray-500 mb-1">
              Plan Effective Date
            </label>
            <input
              type="date"
              value={benefits.plan_effective_date}
              onChange={(e) => handleChange("plan_effective_date", e.target.value)}
              className="input-field"
            />
          </div>
        </div>
      </div>
    </div>
  );
}
