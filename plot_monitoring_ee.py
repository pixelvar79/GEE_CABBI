import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
import calendar
import os

# Create a folder to save figures
output_folder = '../output_figures'
os.makedirs(output_folder, exist_ok=True)
# Read the CSV file
df = pd.read_csv('../check_sentinel_available.csv')

# Convert 'acquisition_date' to datetime
df['acquisition_date'] = pd.to_datetime(df['acquisition_date'])

# Create a new column 'month_name' to represent month names
df['month_name'] = df['acquisition_date'].dt.month.map(lambda x: calendar.month_abbr[x])

# Convert 'month_name' to a categorical type with correct order
month_order = list(calendar.month_abbr)[1:]  # Month names from January to December
df['month_name'] = pd.Categorical(df['month_name'], categories=month_order, ordered=True)

# Check for duplicates within each 'Field Name' and 'sensor_type'
duplicates = df[df.duplicated(['Field Name', 'sensor_type', 'acquisition_date'], keep=False)]

# Display the duplicates
print("Duplicate Rows except first occurrence:")

# Iterate over unique 'Field Name' values
for name in df['Field Name'].unique():
    # Create a new figure for each 'Field Name'
    fig, axes = plt.subplots(figsize=(12, 8), nrows=df['acquisition_year'].nunique(), ncols=1, sharex=True)
    fig.suptitle(f'{name}', fontsize=16)

    # Filter data for the current 'Field Name'
    field_data = df[df['Field Name'] == name]

    # Iterate over unique 'acquisition_year' values
    for idx, year in enumerate(field_data['acquisition_year'].unique()):
        # Filter data for the current 'acquisition_year'
        combo_data = field_data[field_data['acquisition_year'] == year]

        # Calculate the count for each combination of 'month_name' and 'sensor_type'
        counts = combo_data.groupby(['month_name', 'sensor_type']).size().reset_index(name='count')

        # Create a barplot with added space between bars
        sns.barplot(x='month_name', y='count', hue='sensor_type', data=counts, ax=axes[idx], palette='husl',dodge=True)#, width=0.8)
        axes[idx].set_title(f'{year}')

        # Set y-axis limit to 8
        axes[idx].set_ylim(0, 10)

        # Remove y-axis label for individual subplots
        axes[idx].set_ylabel('')

        # Remove legend for individual subplots
        axes[idx].get_legend().remove()

        # Set x-axis label for each subplot
        axes[idx].set_xlabel('Acquisition Month')

        # Set y-axis ticks with a range of 1
        axes[idx].set_yticks(range(0, 11, 2))

        # Annotate each non-zero bar with its value and reduced text size
        for p in axes[idx].patches:
            if p.get_height() > 0:
                axes[idx].annotate(f'{p.get_height():.0f}', (p.get_x() + p.get_width() / 2., p.get_height()),
                                   ha='center', va='center', xytext=(0, 6), textcoords='offset points', fontsize=6)

    # Add legend to the right of the last subplot
    axes[-1].legend(title='Sensor Type', loc='upper left', bbox_to_anchor=(1, 1))

    # Set common y-axis label outside the subplots
    fig.text(0.04, 0.5, 'Number of Acquisitions', ha='center', va='center', rotation='vertical')

    # Adjust layout with increased rect values for better centering
    plt.tight_layout(rect=[0.05, 0, 0.95, 0.96])
    fig_name = f'sentinel_barplot_{name}_{year}.png'
    fig_path = os.path.join(output_folder, fig_name)
    plt.savefig(fig_path)
    plt.close()  # Close the figure to free up resources
    print(f'Figure saved: {fig_path}')

##################################################
# Read the CSV file

# Create a new column 'combined_sensor_type' to aggregate Sentinel-2A and Sentinel-2B
df['combined_sensor_type'] = df['sensor_type'].apply(lambda x: 'Sentinel-2' if 'Sentinel-2' in x else x)

# Iterate over unique 'Field Name' values
for name in df['Field Name'].unique():
    # Create a new figure for each 'Field Name'
    fig, axes = plt.subplots(figsize=(12, 8), nrows=df['acquisition_year'].nunique(), ncols=1, sharex=True)
    fig.suptitle(f'{name}', fontsize=16)

    # Filter data for the current 'Field Name'
    field_data = df[df['Field Name'] == name]

    # Iterate over unique 'acquisition_year' values
    for idx, year in enumerate(field_data['acquisition_year'].unique()):
        # Filter data for the current 'acquisition_year'
        combo_data = field_data[field_data['acquisition_year'] == year]

        # Calculate the count for each combination of 'month_name' and 'combined_sensor_type'
        counts = combo_data.groupby(['month_name', 'combined_sensor_type']).size().reset_index(name='count')

        # Create a barplot with different colors for each combined sensor type
        sns.barplot(x='month_name', y='count', hue='combined_sensor_type', data=counts, ax=axes[idx], palette='husl', dodge=True)
        axes[idx].set_title(f'{year}')

        # Set y-axis limit to 8
        axes[idx].set_ylim(0, 10)

        # Remove y-axis label for individual subplots
        axes[idx].set_ylabel('')

        # Remove legend for individual subplots
        axes[idx].get_legend().remove()

        # Set x-axis label for each subplot
        axes[idx].set_xlabel('Acquisition Month')

        # Set y-axis ticks with a range of 1
        axes[idx].set_yticks(range(0, 11, 1))

        # Annotate each non-zero bar with its value and reduced text size
        for p in axes[idx].patches:
            if p.get_height() > 0:
                axes[idx].annotate(f'{p.get_height():.0f}', (p.get_x() + p.get_width() / 2., p.get_height()),
                                   ha='center', va='center', xytext=(0, 6), textcoords='offset points', fontsize=8)

    # Add legend to the right of the last subplot
    axes[-1].legend(title='Sensor Type', loc='upper left', bbox_to_anchor=(1, 1))

    # Set common y-axis label outside the subplots
    fig.text(0.04, 0.5, 'Number of Acquisitions', ha='center', va='center', rotation='vertical')

    # Adjust layout with increased rect values for better centering
    plt.tight_layout(rect=[0.05, 0, 0.95, 0.96])

    fig_name = f'sentinel_barplot1_{name}_{year}.png'
    fig_path = os.path.join(output_folder, fig_name)
    plt.savefig(fig_path)
    plt.close()  # Close the figure to free up resources
    print(f'Figure saved: {fig_path}')

###############################################################################
# Convert 'acquisition_date' to datetime
df['acquisition_date'] = pd.to_datetime(df['acquisition_date'])

# Create a new column 'month_name' to represent month names
df['month_name'] = df['acquisition_date'].dt.month.map(lambda x: calendar.month_abbr[x])

# Convert 'month_name' to a categorical type with correct order
month_order = list(calendar.month_abbr)[1:]  # Month names from January to December
df['month_name'] = pd.Categorical(df['month_name'], categories=month_order, ordered=True)

# Create separate DataFrames for Sentinel-2 and Sentinel-1
sentinel2_df = df[df['sensor_type'].str.contains('Sentinel-2')]
#sentinel1_df = df[df['sensor_type'].str.contains('Sentinel-1')]

# Fixed color range for heatmaps
vmin, vmax = 0, 10

# Iterate over unique 'acquisition_year' values for Sentinel-2
for year in df[df['sensor_type'].str.contains('Sentinel-2')]['acquisition_year'].unique():
    # Filter data for the current 'acquisition_year' and Sentinel-2
    sentinel2_year_df = sentinel2_df[(sentinel2_df['acquisition_year'] == year)]

    # Aggregate the data by 'Field Name', 'month_name', and count the number of acquisitions
    sentinel2_counts = sentinel2_year_df.groupby(['Field Name', 'month_name']).size().reset_index(name='count')

    # Reshape the DataFrame for heatmap plotting
    sentinel2_heatmap = sentinel2_counts.pivot(index='Field Name', columns='month_name', values='count')

    # Plot the heatmap
    plt.figure(figsize=(12, 8))
    sns.heatmap(sentinel2_heatmap, annot=True, cmap='YlGnBu', cbar_kws={'label': 'Number of Acquisitions'}, vmin=vmin, vmax=vmax)
    plt.title(f'Sentinel-2 Acquisitions - {year}')

    # Save the figure
    fig_name = f'sentinel2_heatmap_{year}.png'
    fig_path = os.path.join(output_folder, fig_name)
    plt.savefig(fig_path)
    plt.close()  # Close the figure to free up resources
    print(f'Figure saved: {fig_path}')

# Iterate over unique 'acquisition_year' values for Sentinel-1
# for year in df[df['sensor_type'].str.contains('Sentinel-1')]['acquisition_year'].unique():
#     # Filter data for the current 'acquisition_year' and Sentinel-1
#     sentinel1_year_df = sentinel1_df[(sentinel1_df['acquisition_year'] == year)]

#     # Aggregate the data by 'Field Name', 'month_name', and count the number of acquisitions
#     sentinel1_counts = sentinel1_year_df.groupby(['Field Name', 'month_name']).size().reset_index(name='count')

#     # Reshape the DataFrame for heatmap plotting
#     sentinel1_heatmap = sentinel1_counts.pivot(index='Field Name', columns='month_name', values='count')

#     # Plot the heatmap
#     plt.figure(figsize=(12, 8))
#     sns.heatmap(sentinel1_heatmap, annot=True, cmap='YlGnBu', cbar_kws={'label': 'Number of Acquisitions'},vmin=vmin, vmax=vmax)
#     plt.title(f'Sentinel-1 Acquisitions - {year}')

#     # Save the figure
#     fig_name = f'sentinel1_heatmap_{year}.png'
#     fig_path = os.path.join(output_folder, fig_name)
#     plt.savefig(fig_path)
#     plt.close()  # Close the figure to free up resources
#     print(f'Figure saved: {fig_path}')
