"""Sortable tree view used for the tables in the server details window."""

from __future__ import annotations

import threading as th
import time
import tkinter as tk
import tkinter.font as tkfont
from tkinter import ttk

from client.errors import show_error


class StatisticsTreeUI(tk.Frame):

    def __init__(
            self,
            *args,
            columns=[],
            formats=[],
            data={},
            sort=-1,
            reverse=True,
            **kwargs
    ):

        super().__init__(*args, **kwargs)

        self.columns = columns
        self.formats = formats
        self.data = data
        self.sort = sort
        self.reverse = reverse
        self.query = ""

        # Tree frame

        self.tree_frame = tk.Frame(self)
        self.tree_frame.grid(row=0, column=0, columnspan=2)

        # Tree canvas

        self.tree_canvas = tk.Canvas(
            self.tree_frame,
            width=350,
            height=323,
            bg="white",
            highlightthickness=0
        )
        self.tree_canvas.pack(side="left")

        # Tree

        column_ids = []
        for column in columns:
            column_ids.append(column[0])
        column_ids = tuple(column_ids[1:])

        self.tree = ttk.Treeview(
            self.tree_canvas,
            columns=column_ids,
            selectmode="browse",
            height=15
        )
        self.tree.bind("<<TreeviewOpen>>", self.on_item_expand)
        self.tree.bind("<<TreeviewClose>>", self.on_item_expand)
        self.tree.bind("<Double-1>", self.on_click)
        self.tree.bind("<Button-1>", self.on_click)

        for column in columns:
            column_id = column[0]
            column_name = column[1]
            column_width = column[2]
            column_anchor = column[3]
            self.tree.column(
                column_id,
                width=column_width,
                anchor=column_anchor,
                stretch=False
            )
            self.tree.heading(
                column_id,
                text=column_name,
                command=lambda index=columns.index(column): self.on_header_click(index)
            )

        self.sort_data()
        self.populate_treeview()

        # self.master.configure(width=sum([column[2] for column in columns]))
        self.tree.pack()
        self.tree_canvas.create_window(0, 0, window=self.tree, anchor="nw")

        self.after(100, self.filter_treeview)

        # Scrollbar

        self.scrollbar = ttk.Scrollbar(
            self.tree_frame, orient="vertical", command=self.tree.yview
        )
        self.scrollbar.pack(side="right", fill="y")
        self.tree.configure(yscrollcommand=self.scrollbar.set)

        # Button

        self.button = ttk.Button(self, text="Button")
        self.button.grid(
            row=1, column=0, sticky="nw", padx=(0, 10), pady=(10, 0)
        )

        # Entry

        self.entry = ttk.Entry(self)
        self.entry.grid(
            row=1, column=1, sticky="ne", padx=(10, 15), pady=(12, 0)
        )

    def sort_data(self):

        sorted_items = sorted(
            self.data.items(),
            key=lambda item: item[1][self.sort],
            reverse=self.reverse
        )
        self.data = {key: entry for key, entry in sorted_items}

    def populate_treeview(self, parent=""):

        # Get all child items of the parent item
        children: list[str] = list(self.tree.get_children(parent))

        # Set index for insertion
        index = 0

        # Loop through each item, format it, and add it to the tree
        for item, entry in self.data.items():

            # Generate search field for query
            field = ""
            for value in entry:
                if type(value) is str:
                    field += value

            # Format the data
            entry = entry.copy()
            for i in range(len(entry)):
                try:
                    entry[i] = self.formats[i](entry[i])
                except Exception as e:
                    entry[i] = f"ERROR: {e}"

            # Divide the entry into text (column #0) and values (columns #1)
            text: str = entry[0]
            values = entry[1:]

            # If item satisfies the query
            if len(self.query) < 1 or self.query.lower() in field.lower():

                # If item in tree
                if item not in children:

                    # Insert the item into the tree
                    self.tree.insert(
                        "", index, id=item, text=text, values=values
                    )
                    children.insert(index, item)

                # Increment the index for insertion
                index += 1

            # If item does not satisfy query
            else:

                # If item in tree
                if item in children:

                    # Remove the item
                    self.tree.delete(item)
                    children.remove(item)

    def filter_treeview(self):

        try:

            query = self.entry.get()

            if query != self.query:

                self.query = query

                self.populate_treeview()

        except Exception as e:

            show_error(
                f"An error occurred while filtering.\n\n{e}", no_ui=True
            )

            # self.query = query

            # Cache the tree structure if not already cached
            # if not hasattr(self, "original_tree"):
            #    self.original_tree = {}
            #    self.original_indices = {}

            #    def cache_tree_structure(parent):
            #        """Recursively cache the tree structure and indices."""
            #        children = tree.get_children(parent)
            #        self.original_tree[parent] = children
            # self.original_indices[parent] = {child: idx for idx, child in
            # enumerate(children)}
            #        for child in children:
            #            cache_tree_structure(child)
            #
            #    cache_tree_structure("")

            # def recursive_filter(parent, query):
            #    """Recursively filter the items in the tree."""
            #    match_found = False  # Tracks if any child matches the query

            #    visible_children = []

            #    for child in self.original_tree.get(parent, []):
            #        # Get the text of the current item
            #        item_text = tree.item(child, "text").lower()
            # child_match = query in item_text if query else True  # Match all
            # if query is empty

            #        # Recursively filter the children of this child
            #        child_visible = recursive_filter(child, query)

            #        # Show this item if it or any of its descendants match
            #        if child_match or child_visible:
            #            visible_children.append(child)
            #            match_found = True
            #        else:
            #            if child in tree.get_children(parent):
            #                tree.detach(child)  # Detach the item

            # Reattach children in original order
            #    for child in visible_children:
            #        tree.reattach(child, parent, "end")

            #    return match_found

            # if not query:
            # Reset the tree to its original structure
            #    def reset_tree(parent):
            #        children = self.original_tree.get(parent, [])
            #        for child in children:
            #            if child not in tree.get_children(parent):
            #                tree.reattach(child, parent, "end")
            #            reset_tree(child)

            #    reset_tree("")
            # else:
            #    # Start recursive filtering from the root
            #    recursive_filter("", query)

        # Continue filtering periodically
        self.after(100, self.filter_treeview)

    def on_click(self, event):

        region = self.tree.identify_region(event.x, event.y)
        if region == "separator":
            return "break"

    def on_item_expand(self, event):

        th.Thread(target=self.adjust_tree_column_widths).start()

    def on_header_click(self, index):

        # Get current selection (to be reselected after sorting)
        selection = self.tree.selection()

        # Set sort mode
        if index == self.sort:
            self.reverse = not self.reverse
        else:
            if self.columns[index][1] in ["Name", "Mayor"]:
                self.reverse = False
            else:
                self.reverse = True
        self.sort = index

        # Clear the tree
        for item in self.tree.get_children(""):
            self.tree.delete(item)

        # Sort the data
        self.sort_data()

        # Populate the tree
        self.populate_treeview()

        # Re-add the selection (if any)
        if len(selection) > 0:
            self.tree.selection_add(selection)
            self.tree.focus(selection[0])

    def adjust_tree_column_widths(self):
        """
        Adjusts column widths on the TreeView to fit contents.

        Trash code written by Chat-GPT
        """

        try:

            time.sleep(.2)  # Give time for the item to actually expand

            tree = self.tree

            # Get the style used in the Treeview
            font_name = "TkDefaultFont"
            font = tkfont.nametofont(font_name)

            indent = 40  # Default indentation for Treeview items (can be customized)

            # Adjust the #0 column (tree column)
            # font.measure(tree.heading("#0")["text"])  # Start with header
            # width
            max_width = tree.column("#0", option="width")

            def calculate_width(item, level=0):

                nonlocal max_width

                children = tree.get_children(item)

                # Calculate the width of the item's text in the #0 column
                cell_content = tree.item(item, "text")
                item_width = font.measure(cell_content) + (level * indent)
                max_width = max(max_width, item_width)

                # Recursively calculate widths for child items
                if tree.item(item, "open"):
                    for child in children:
                        calculate_width(child, level + 1)

            # Process root-level items and their children for #0 column
            for root_item in tree.get_children(""):
                calculate_width(root_item)

            # Set the #0 column width to the calculated maximum
            tree.column("#0", width=min(1000, max_width))

            # Adjust other columns
            # for col in tree["columns"]:

            # max_width = tree.column(col, option="width") #font.measure(col)
            # # Start with column header width

            #    def calculate_column_width(item, level=0):

            #        nonlocal max_width

            #        # Calculate the width of the current item's content in this column
            #        cell_content = tree.set(item, col)
            #        item_width = font.measure(cell_content)
            #        max_width = max(max_width, item_width)

            #        # Recursively calculate widths for child items
            #        if tree.item(item, "open"):
            #            for child in tree.get_children(item):
            #                calculate_column_width(child, level + 1)

            #    # Process root-level items and their children for each column
            #    for root_item in tree.get_children(""):
            #        calculate_column_width(root_item)

            #    # Set the column width to the calculated maximum
            #    tree.column(col, width=max_width)

        except Exception as e:

            show_error(f"Failed to adjust column widths.\n\n{e}", no_ui=True)

    def get_tree_width(self):

        width = self.tree.column("#0", "width")

        for column in self.tree["columns"]:
            try:
                if self.tree.heading(column, "text") != "⠀":
                    width += self.tree.column(column, option="width")
            except BaseException:
                pass

        return width

    def winfo_width(self):

        # print(self.tree_canvas.configure("width"))
        # self.scrollbar.lift()

        tree_width = self.get_tree_width()

        self.tree_canvas.configure(width=tree_width - 2)

        return tree_width + 20

    def winfo_height(self):

        return 361
