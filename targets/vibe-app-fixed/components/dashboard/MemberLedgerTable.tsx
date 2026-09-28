import * as s from "./tableStyles";

export default function MemberLedgerTable({ members }: { members: any[] }) {
  return (
    <section style={s.section}>
      <h2 style={s.sectionTitle}>Member credit ledger</h2>
      <table style={s.table}>
        <thead>
          <tr style={s.headRow}>
            <th style={s.th}>Name</th>
            <th style={s.th}>Email</th>
            <th style={s.th}>Role</th>
            <th style={s.th}>Credit balance</th>
          </tr>
        </thead>
        <tbody>
          {members.map((member) => {
            const isLow = member.credit_balance <= 2;
            return (
              <tr key={member.id} style={s.bodyRow}>
                <td style={s.td}>{member.full_name}</td>
                <td style={s.td}>{member.email}</td>
                <td style={s.td}>{member.role}</td>
                <td style={{ ...s.td, color: isLow ? "#b45309" : "#1a1a1a", fontWeight: isLow ? 700 : 400 }}>
                  {member.credit_balance}
                  {isLow ? " (low)" : ""}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </section>
  );
}
