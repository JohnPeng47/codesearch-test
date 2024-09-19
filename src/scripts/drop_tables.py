import click
from sqlalchemy import inspect, Table, MetaData
from src.database.core import engine
from src.repo.repository import GitRepo
from sqlalchemy.orm import sessionmaker


@click.group()
def cowboy_database():
    pass

@cowboy_database.command("drop-table")
@click.argument('table_name')
@click.option('--confirm', is_flag=True, help="Confirm the operation without prompting")
def drop_table(table_name, confirm):
    """Drops all data from the specified table."""
    Session = sessionmaker(bind=engine)
    session = Session()
    
    inspector = inspect(engine)
    if table_name not in inspector.get_table_names():
        click.echo(f"Table '{table_name}' does not exist in the database.")
        return

    if not confirm:
        click.confirm(f"Are you sure you want to drop all data from the '{table_name}' table?", abort=True)

    try:
        metadata = MetaData()
        table = Table(table_name, metadata, autoload_with=engine)
        
        # Delete all rows
        session.execute(table.delete())
        session.commit()
        click.echo(f"All data from table '{table_name}' has been deleted.")
        
        if table_name == "repos":
            for row in session.query(table).all():
                click.echo(f"Deleting repo: {row.file_path}")
                GitRepo.delete_repo(row.file_path)

            click.echo("All repos have been deleted.")

    except Exception as e:
        session.rollback()
        click.echo(f"An error occurred: {str(e)}")
    finally:
        session.close()

if __name__ == "__main__":
    cowboy_database()