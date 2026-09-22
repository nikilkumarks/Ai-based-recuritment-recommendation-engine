import { PageHeader } from "@/components/ui/page-header";
import { EmptyState } from "@/components/ui/empty-state";

export default function AdminUsersPage() {
  return (
    <div>
      <PageHeader
        title="Users / organizations"
        description="Account management is not exposed as a directory in this product. Registration creates candidate and recruiter accounts; admin accounts are provisioned separately."
      />
      <EmptyState
        title="No user directory API is available."
        description="This page is a workspace placeholder so admin navigation is complete without inventing a user table."
      />
    </div>
  );
}
