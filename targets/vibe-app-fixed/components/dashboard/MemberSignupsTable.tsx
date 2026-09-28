import * as s from "./tableStyles";

export default function MemberSignupsTable({ members }: { members: any[] }) {
  const sorted = [...members].sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime());
  return (
    <section style={s.section}>
      <h2 style={s.sectionTitle}>Member signups</h2>
      <table style={s.table}>
        <thead>
          <tr style={s.headRow}>
            <th style={s.th}>Name</th>
            <th style={s.th}>Email</th>
            <th style={s.th}>Role</th>
            <th style={s.th}>Signed up</th>
          </tr>
        </thead>
        <tbody>
          {sorted.map((member) => (
            <tr key={member.id} style={s.bodyRow}>
              <td style={s.td}>{member.full_name}</td>
              <td style={s.td}>{member.email}</td>
              <td style={s.td}>{member.role}</td>
              <td style={s.td}>{new Date(member.created_at).toLocaleDateString()}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}
