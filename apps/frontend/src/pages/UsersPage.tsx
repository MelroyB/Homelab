import { useEffect, useState } from "react";
import { listUsers } from "../api/auth";
import { User } from "../types/api";

export function UsersPage() {
  const [users, setUsers] = useState<User[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    listUsers()
      .then(setUsers)
      .catch((err) => setError(err instanceof Error ? err.message : "Failed to load users"));
  }, []);

  return (
    <section>
      <h2>Users</h2>
      {error ? <div className="error">{error}</div> : null}
      <table className="table card">
        <thead>
          <tr>
            <th>Email</th>
            <th>Role</th>
            <th>Status</th>
          </tr>
        </thead>
        <tbody>
          {users.map((user) => (
            <tr key={user.id}>
              <td>{user.email}</td>
              <td>{user.role}</td>
              <td>{user.is_active ? "active" : "disabled"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}
