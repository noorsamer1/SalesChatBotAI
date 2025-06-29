import { useReactTable, getCoreRowModel, flexRender } from '@tanstack/react-table';

export default function TableMessage({ data }) {
    const { title, columns: columnNames, rows } = data;

    if (!columnNames || !rows) {
        return <div>⚠️ No table data available.</div>;
    }

    // Step 1: Create column definitions for TanStack
    const columns = columnNames.map((colName, idx) => ({
        accessorKey: colName,
        header: colName,
    }));

    // Step 2: Format row data into array of objects (TanStack expects objects)
    const formattedRows = rows.map((rowArray) => {
        const rowObj = {};
        columnNames.forEach((colName, idx) => {
            rowObj[colName] = rowArray[idx];
        });
        return rowObj;
    });

    // Step 3: Create table instance
    const table = useReactTable({
        data: formattedRows,
        columns,
        getCoreRowModel: getCoreRowModel(),
    });

    // Step 4: Render table
    return (
        <div>
            <h4>{title}</h4>
            <table style={{ width: "100%", borderCollapse: "collapse", marginTop: "10px" }}>
                <thead>
                    {table.getHeaderGroups().map((headerGroup) => (
                        <tr key={headerGroup.id}>
                            {headerGroup.headers.map((header) => (
                                <th
                                    key={header.id}
                                    style={{ border: "1px solid #ccc", padding: "5px", textAlign: "left" }}
                                >
                                    {flexRender(header.column.columnDef.header, header.getContext())}
                                </th>
                            ))}
                        </tr>
                    ))}
                </thead>
                <tbody>
                    {table.getRowModel().rows.map((row) => (
                        <tr key={row.id}>
                            {row.getVisibleCells().map((cell) => (
                                <td key={cell.id} style={{ border: "1px solid #ccc", padding: "5px" }}>
                                    {flexRender(cell.column.columnDef.cell, cell.getContext())}
                                </td>
                            ))}
                        </tr>
                    ))}
                </tbody>
            </table>
        </div>
    );
}
