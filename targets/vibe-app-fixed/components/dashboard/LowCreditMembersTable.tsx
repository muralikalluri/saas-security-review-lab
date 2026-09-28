import * as s from "./tableStyles";

export default function LowCreditMembersTable({ members }: { members: any[] }) {
  return (
    <section style={s.section}>
      <h2 style={s.sectionTitle}>Low-credit members (2 or fewer)</h2>
      <table style={s.table}>
        <thead>
          <tr style={s.headRow}>
            <th style={s.th}>Name</th>
            <th style={s.th}>Email</th>
            <th style={s.th}>Credit balance</th>
          </tr>
        </thead>
        <tbody>
          {members.map((member) => (
            <tr key={member.id} style={s.bodyRow}>
              <td style={s.td}>{member.full_name}</td>
              <td style={s.td}>{member.email}</td>
              <td style={{ ...s.td, color: "#b45309", fontWeight: 700 }}>{member.credit_balance}</td>
            </tr>
          ))}
          {members.length === 0 ? (
            <tr>
              <td style={s.td} colSpan={3}>
                No members below the threshold.
              </td>
            </tr>
          ) : null}
        </tbody>
      </table>
    </section>
  );
}
