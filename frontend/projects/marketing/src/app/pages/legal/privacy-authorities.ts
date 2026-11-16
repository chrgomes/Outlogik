/**
 * Privacy regulators, for "How to complain". Federal (PIPEDA) always; provinces with their own
 * private-sector privacy law as well.
 */
export interface Authority {
  name: string;
  url: string;
}

export const FEDERAL_AUTHORITY: Authority = {
  name: 'Office of the Privacy Commissioner of Canada', url: 'https://www.priv.gc.ca',
};

export const PROVINCIAL_AUTHORITIES: Record<string, Authority & { law: string }> = {
  Quebec: {
    name: "Commission d'accès à l'information du Québec", url: 'https://www.cai.gouv.qc.ca',
    law: 'the Act respecting the protection of personal information in the private sector',
  },
  'British Columbia': {
    name: 'Office of the Information and Privacy Commissioner for British Columbia', url: 'https://www.oipc.bc.ca',
    law: 'the Personal Information Protection Act (British Columbia)',
  },
  Alberta: {
    name: 'Office of the Information and Privacy Commissioner of Alberta', url: 'https://oipc.ab.ca',
    law: 'the Personal Information Protection Act (Alberta)',
  },
};
