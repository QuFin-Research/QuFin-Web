/** Decided by the API from its settings, never chosen at sign-up. */
export type Role = 'admin' | 'data_scientist' | 'user';

export type User = {
  id: string;
  email: string;
  createdAt: string;
  role: Role;
};

export type Credentials = {
  email: string;
  password: string;
};
