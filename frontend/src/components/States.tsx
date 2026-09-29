import { Button, Spinner, Text } from "@fluentui/react-components";
import { Link } from "react-router-dom";

export function LoadingState({ label }: { label: string }) {
  return (
    <div className="panel" role="status">
      <Spinner label={label} />
    </div>
  );
}

export function ErrorState({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div className="panel" role="alert">
      <Text weight="semibold">Something went wrong</Text>
      <p>{message}</p>
      {onRetry ? (
        <Button appearance="primary" onClick={onRetry}>
          Try again
        </Button>
      ) : null}
    </div>
  );
}

export function EmptyState({
  title,
  body,
  action,
}: {
  title: string;
  body: string;
  action?: { to: string; label: string };
}) {
  return (
    <div className="panel">
      <Text weight="semibold">{title}</Text>
      <p className="muted">{body}</p>
      {action ? (
        <Link to={action.to}>
          <Button appearance="primary">{action.label}</Button>
        </Link>
      ) : null}
    </div>
  );
}
