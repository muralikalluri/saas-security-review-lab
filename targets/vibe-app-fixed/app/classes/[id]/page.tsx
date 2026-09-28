import { getClassById } from "@/lib/data/classes";
import BookingForm from "@/components/BookingForm";

export default async function ClassDetailPage({ params }: { params: { id: string } }) {
  const classRow = await getClassById(params.id);

  if (!classRow) {
    return <main>Class not found.</main>;
  }

  return (
    <main>
      <h1>{classRow.title}</h1>
      <p>
        {classRow.instructor} - {classRow.studio_name}
      </p>
      <p>{new Date(classRow.starts_at).toLocaleString()}</p>
      <BookingForm classId={classRow.id} creditCostPerSeat={classRow.credit_cost} />
    </main>
  );
}
